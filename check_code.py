import cv2
import numpy as np
from session import Session
import os
import logging

from datetime import datetime

TEMP_PATH = './temp/'


class CheckCode:

    def __init__(self, sess: Session = Session()):
        self.sess = sess
        try:
            self.check_code()
        except:
            logging.error('验证码处理时出错')

    def check_code(self, code=None, flag=True):  # 是否传入验证码,是否第一次验证码错误
        """
        验证码识别，参数为checkcode和isFirst，用于标识是否为第一次验证码识别，
        第一次识别需要下载验证码，由于文书验证码验证经常出现验证码正确但
        但会验证码错误情况，所以第一次验证码错误时不会下载新的验证码.
        """
        if code is None:
            check_code_url = 'http://wenshu.court.gov.cn/User/ValidateCode'
            headers = {
                'Host': 'wenshu.court.gov.cn',
                'Origin': 'http://wenshu.court.gov.cn',
                'User-Agent': self.sess.user_agent
            }
            r = self.sess.get(url=check_code_url, headers=headers)
            pic_path = os.path.join(TEMP_PATH, 'checkCode.jpg')
            with open(pic_path, 'wb') as f:
                f.write(r.content)
            # with open(TEMP_PATH + datetime.now().strftime('%Y-%m-%d %H-%M-%S-%f') + '.jpg', 'wb') as f:
            #     f.write(r.content)
            code = input('请输入验证码：')
            # code = self._distinguish(pic_path)
        logging.info('验证码为：{0}'.format(code))
        check_url = 'http://wenshu.court.gov.cn/Content/CheckVisitCode'
        headers = {
            'Host': 'wenshu.court.gov.cn',
            'Origin': 'http://wenshu.court.gov.cn',
            'Referer': 'http://wenshu.court.gov.cn/Html_Pages/VisitRemind.html',
            'User-Agent': self.sess.user_agent
        }
        data = {
            'ValidateCode': code
        }
        req = self.sess.post(url=check_url, data=data, headers=headers)
        if req.text == '2':
            logging.error('验证码错误')
            if flag:
                self.check_code(code, False)
            else:
                self.check_code()
        else:
            logging.info('验证码正确：{0}'.format(code))

    # 两张图片的相似程度
    @staticmethod
    def _mse(image1, image2):
        err = np.sum((image1.astype(float) - image2.astype(float)) ** 2)
        err /= float(image1.shape[0] * image1.shape[1])
        return err

    # 切割后的验证码最接近什么数字/字母
    def _compare(self, image):
        count = 999999
        result = 0
        for i in range(0, 9):
            image_com = cv2.imread('./train/{0}.jpg'.format(i))
            mse_res = self._mse(image, image_com)
            if mse_res < count:
                result = i
                count = mse_res
        return result

    # 验证码识别
    def _distinguish(self, file_path):
        # 读取图片
        image = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)

        # 擦除噪点和干扰线
        kernel = np.ones((1, 1), np.uint8)
        erosion = cv2.erode(image, kernel, iterations=1)

        # 模糊操作
        blurred = cv2.GaussianBlur(erosion, (5, 5), 0)

        # 边界
        edged = cv2.Canny(blurred, 30, 60)

        # 膨胀
        dilation = cv2.dilate(edged, kernel, iterations=1)

        # 侦测轮廓
        image, contours, hierarchy = cv2.findContours(dilation.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        cnts = sorted([(c, cv2.boundingRect(c)[0]) for c in contours], key=lambda x: x[1])

        arr = []
        for (c, _) in cnts:
            (x, y, w, h) = cv2.boundingRect(c)
            if 9 <= w <= 13 and 15 <= h <= 19:
                Flag = False
                for i in range(-2, 3):
                    for j in range(-2, 3):
                        for k in range(-2, 3):
                            for l in range(-2, 3):
                                if (x + i, y + j, w + k, h + l) in arr:
                                    Flag = True
                                    break
                            if Flag:
                                break
                        if Flag:
                            break
                    if Flag:
                        break
                if not Flag:
                    arr.append((x, y, w, h))
        check_result = ''
        for item in arr:
            (x, y, w, h) = item
            img = dilation[y:y + h, x:x + w]
            res = cv2.resize(img, (12, 18))
            cv2.imwrite(os.path.join(TEMP_PATH, 'split.jpg'), res)
            res = cv2.imread(os.path.join(TEMP_PATH, 'split.jpg'))
            check_result += str(self._compare(res))
        return check_result
