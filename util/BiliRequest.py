import requests

from util.CookieManager import CookieManager


class BiliRequest:
    def __init__(self, headers=None, cookies_config_path=""):
        self.session = requests.Session()
        self.cookieManager = CookieManager(cookies_config_path)
        self.headers = headers or {
            "authority": "show.bilibili.com",
            "accept": "*/*",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6,zh-TW;q=0.5,ja;q=0.4",
            "cookie": "",
            "referer": "https://mall.bilibili.com/",
            "content-type": "application/x-www-form-urlencoded",
            "sec-ch-ua": '"Microsoft Edge";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "App-key": "iphone",
            "native_api_from": "h5",
            "x-risk-header": "appkey/27eb53fc9058f8c3 mVersion/263 model/iPhone%2015%20Pro mallVersion/8020000 brand/Apple osver/18.0(22A5297f) platform/h5 uid/511430390 channel/1 deviceId/Y644A66257297B0F4814AC6531429586A01B sLocale/zh-Hans_CN cLocale/zh-Hans_CN identify/appkey%3D27eb53fc9058f8c3%26sign%3Dd548d09d0dee2f90d8be19c311c424e0%26ts%3D1719588525000",
            "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/619.1.18.10.1 (KHTML, like Gecko) Mobile/22A5297f BiliApp/80200100 os/ios model/iPhone 15 Pro mobi_app/iphone build/80200100 osVer/18.0 network/2 channel/AppStore Buvid/Y644A66257297B0F4814AC6531429586A01B c_locale/zh-Hans_CN s_locale/zh-Hans_CN sessionID/840149c9 disable_rcmd/0 mallVersion/8020000 mVersion/263 flutterNotch/1",
        }

    def get(self, url, data=None):
        self.headers["cookie"] = self.cookieManager.get_cookies_str()
        response = self.session.get(url, data=data, headers=self.headers)
        response.raise_for_status()
        if response.json().get("msg", "") == "请先登录":
            self.headers["cookie"] = self.cookieManager.get_cookies_str_force()
            self.get(url, data)
        return response

    def post(self, url, data=None):
        self.headers["cookie"] = self.cookieManager.get_cookies_str()
        response = self.session.post(url, data=data, headers=self.headers)
        response.raise_for_status()
        if response.json().get("msg", "") == "请先登录":
            self.headers["cookie"] = self.cookieManager.get_cookies_str_force()
            self.post(url, data)
        return response

    def get_request_name(self):
        try:
            if not self.cookieManager.have_cookies():
                return "未登录"
            result = self.get("https://api.bilibili.com/x/web-interface/nav").json()
            return result["data"]["uname"]
        except Exception as e:
            return "未登录"


