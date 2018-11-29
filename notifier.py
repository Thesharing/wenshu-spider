import logging
import atexit
import os
from math import ceil
from abc import abstractmethod
from typing import List, Union

import smtplib
from email.header import Header
from email.mime.text import MIMEText
from email.utils import parseaddr, formataddr

from apscheduler.schedulers.background import BlockingScheduler, BackgroundScheduler
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_MAX_INSTANCES
from apscheduler.schedulers.base import STATE_STOPPED

import itchat

from persistence import Database, test_redis, test_mongodb


class Notifier:
    def __init__(self, databases: List[Database], ongoing: str, saved: str, period: int, background: bool = False):
        test_redis()
        test_mongodb()
        self.last_saved_count = 0
        self.average = 0
        self.batch = 0
        self.databases = databases
        self.ongoing = ongoing
        self.saved = saved
        self.period = period
        self.logger = logging.getLogger('notifier')
        if background:
            self.scheduler = BackgroundScheduler()
        else:
            self.scheduler = BlockingScheduler()
        self.scheduler.add_listener(self.listen, EVENT_JOB_ERROR | EVENT_JOB_MAX_INSTANCES)
        self.scheduler.add_job(self.work, 'interval', minutes=self.period, id='notifier', coalesce=False,
                               max_instances=1)
        atexit.register(self.exit)

    def watch(self):
        output = '[{}] '.format(self.batch + 1)
        ongoing_count = 0
        saved_count = 0
        for database in self.databases:
            count = database.count()
            output += '{0}({1}): {2} items | '.format(database.name, database.type, count)
            if database.name == self.ongoing:
                ongoing_count = count
            elif database.name == self.saved:
                saved_count = count
        if self.batch > 0:
            progress_count = saved_count - self.last_saved_count
            self.average = (self.average * (self.batch - 1) + progress_count) / self.batch
            speed = ceil(self.average * (60 / self.period))
            eta = ongoing_count / speed
            output += 'Download: {} items | Average: {} item/h | ETA: {} hours'.format(progress_count, speed, eta)
        self.last_saved_count = saved_count
        self.batch += 1
        return output

    def listen(self, event):
        if event.exception:
            self.logger.error(str(event.exception))

    def run(self):
        self.login()
        self.scheduler.start()

    @abstractmethod
    def login(self):
        raise NotImplementedError

    @abstractmethod
    def work(self):
        raise NotImplementedError

    @abstractmethod
    def exit(self):
        raise NotImplementedError


class WeChatNotifier(Notifier):

    def __init__(self, databases: List[Database], ongoing: str, saved: str, period: int, background: bool = False,
                 receiver: str = 'filehelper', scan_in_cmd: Union[bool, int] = False):
        """
        :param databases: list of databases
        :param ongoing: the database name that contains ongoing DocID
        :param saved: the database name that contains finished DocID
        :param period: watching frequency (minutes)
        :param background: to run background or blocking
        :param receiver: the username of msg receiver
        :param scan_in_cmd: show the QR Code in cmd or save the QRCode into pic
        """
        super(WeChatNotifier, self).__init__(databases, ongoing, saved, period, background)
        self.receiver = receiver
        self.scan_in_cmd = scan_in_cmd

    def login(self):
        dir_path = os.path.abspath('./temp/qrcode.jpg')
        self.logger.info('QRCode Picture is saved in {}, please use WeChat app scan it.'.format(dir_path))
        itchat.auto_login(picDir=dir_path, enableCmdQR=self.scan_in_cmd)

    def work(self):
        while True:
            try:
                output = self.watch()
                self.logger.info(output)
                res = itchat.send(output, self.receiver)
                if res['BaseResponse']['Ret'] > 0:
                    self.logger.error('Error when send msg: Require Log Again.')
                    itchat.logout()
                    self.login()
                    continue
                break
            except KeyError:
                self.logger.error('Key Error: Require Log Again.')
                itchat.logout()
                self.login()

    def exit(self):
        itchat.logout()
        if self.scheduler.state != STATE_STOPPED:
            self.scheduler.shutdown(wait=False)


class EmailNotifier(Notifier):

    def __init__(self, databases: List[Database], ongoing: str, saved: str, period: int, sender: str, password: str,
                 server_addr: str, receiver: Union[str, None] = None, ssl: bool = False, server_port: int = 25,
                 background: bool = False):
        super(EmailNotifier, self).__init__(databases, ongoing, saved, period, background)
        self.sender = sender
        self.password = password
        if receiver is None:
            self.receiver = sender
        else:
            self.receiver = receiver
        self.server_addr = server_addr
        self.server_port = server_port
        self.enable_ssl = ssl
        self.server = smtplib.SMTP(self.server_addr, self.server_port)
        self.server.set_debuglevel(2)

    def login(self):
        if self.enable_ssl:
            self.server.starttls()
        self.server.login(self.sender, self.password)

    def work(self):
        output = self.watch()
        self.logger.info(output)
        msg = MIMEText(output, 'plain', 'utf-8')
        msg['From'] = self._format_addr('Notifier <%s>' % self.sender)
        msg['To'] = self._format_addr('Admin <%s>' % self.receiver)
        msg['Subject'] = Header('Notification', 'utf-8').encode()
        self.server.sendmail(from_addr=self.sender, to_addrs=[self.receiver], msg=msg.as_string())

    def exit(self):
        self.server.quit()
        if self.scheduler.state != STATE_STOPPED:
            self.scheduler.shutdown(wait=False)

    def _format_addr(self, s):
        name, addr = parseaddr(s)
        return formataddr((Header(name, 'utf-8').encode(), addr))
