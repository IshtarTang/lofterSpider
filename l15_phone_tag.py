import json
import sys
import time

import requests
from requests.cookies import create_cookie


class phone_lofter_spider:
    def __init__(self, headers, cookies, tag, list_type="total", timelimit="", blog_type=""):
        self.session = requests.session()
        self.session.headers = headers
        for name, value in cookies.items():
            cookie = create_cookie(domain="api.lofter.com", name=name, value=value)
            self.session.cookies.set_cookie(cookie)
        self.tag = tag

        self.data = {
            "product": "lofter-android-7.9.7.2",
            "postTypes": blog_type,
            "offset": "0",
            "postYm": timelimit,
            "recentDay": "0",
            "protectedFlag": "0",
            "range": "0",
            "firstpermalink": "null",
            "style": "0",
            "tag": self.tag,
            "type": list_type
        }

    def update_data(self, json_response):
        """
        更新data里的offset
        :param json_response: 上一次请求的响应，里边有offset
        :return:
        """
        offset = json_response["data"]["offset"]
        self.data["offset"] = str(offset)

    def update_NTESwebSI(self):
        """
        # 请求之后会更新cookies中的NTESwebSI，一个NTESwebSI只能用来请求一组tag页面数据
        :return:
        """
        self.session.post("https://api.lofter.com/v1.1/newTag.api")

    def get_tag_data(self):
        """
        获取tag页的数据
        :return:
        """
        tag_data_url = 'https://api.lofter.com/newapi/tagPosts.json'
        count = 0
        tag_data = []
        permalinks = set()
        while True:
            # 更新NTESwebSI -> 发请求 -> 更新data
            self.update_NTESwebSI()
            response = self.session.post(tag_data_url, data=self.data, verify=False)
            self.update_data(response.json())
            c_tag_data = response.json()["data"]["list"]

            # 上限是100页，tag中数量够的话100页之后返回空；如果tag总页数没有100，翻完了会从头开始，用是否已经存过来判断
            if not c_tag_data or c_tag_data[0]["postData"]["postView"]["permalink"] in permalinks:
                print("tag页信息获取结束")
                break

            tag_data += c_tag_data
            for bolg_info in c_tag_data:
                permalinks.add(bolg_info["postData"]["postView"]["permalink"])

            # 这一坨都是测试打印
            print(len(c_tag_data))
            a_blog = c_tag_data[0]
            pc_link = f'https://{a_blog["blogInfo"]["blogName"]}.lofter.com/post/{a_blog["postData"]["postView"]["permalink"]}'
            digest = a_blog["postData"]["postView"]["digest"]
            hot_count = a_blog["postData"]["postCount"]["hotCount"]
            print(pc_link, hot_count, digest)

            count += 1
            print(f"请求tag page {count}")
            time.sleep(0.5)


        return tag_data

    def get_blog_info(self, blog_info):
        """
        请求博客页面
        :param blog_info:
        :return:
        """
        url = 'https://api.lofter.com/oldapi/post/detail.api'
        data = {
            "targetblogid": blog_info["blogInfo"]["blogId"],
            "supportposttypes": "1%%2C2%%2C3%%2C4%%2C5%%2C6",
            "blogdomain": f"{blog_info['blogInfo']['blogName']}.lofter.com",
            "offset": "0",
            "requestType": "0",
            "postdigestnew": "1",
            "postid": str(blog_info["postData"]["postView"]["id"]),
            "checkpwd": "1",
            "needgetpoststat": "1"
        }
        params = {
            "product": "lofter-android-7.9.7.2"
        }
        # 这里就弄到博客详情页了
        response = requests.post(url, data=data, params=params)
        json.dump(response.json(), open("blog.json", "w", encoding="utf-8"), ensure_ascii=False, indent=4)
        return response.json()


if __name__ == '__main__':
    """
    这个程序主要就确认了一下tag页和博客页这两接口的数据能搞到，然后大概搞了个结构出来
    不能直接使
    
    """

    # 虽然要了很多但其实一个都不查
    headers = {
        # "X-device": "0uXszt9pWgulCAAkQejjyT4vg4j6IEFPUF6C/wzQG0TG7FyXceCOhMfSRn21F86X",
        # "lofProduct": "lofter-android-7.9.7.2",
        # "User-Agent": "LOFTER-Android 7.9.7.2 (PCT-AL10; Android 10; null) MOBILE",
        # "LOFTER-PHONE-LOGIN-AUTH": "",
        # "market": "huawei",
        # "deviceid": "393aa62fe6cf1a49",
        # "dadeviceid": "2fa6522a5e7128777fa827c928c37c442abf373b",
        # "androidid": "393aa62fe6cf1a49",
        # "X-REQID": "XUALLYK1",
        "Accept-Encoding": "gzip",
        # "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
        "Host": "api.lofter.com",
        "Connection": "Keep-Alive"
    }
    cookies = {
        # "usertrack": "",
        # "NEWTOKEN": "",
    }

    list_type = "total"  # total-总榜 month-月榜 week-周榜 date-日榜
    timelimit = ""  # 总榜可以开月份筛选 格式：yyyyMM  例：202404
    blog_type = ""  # 1是只要文字博客，2是只要图片博客，空字符串是全都要
    tag = "冬兵"  # 就是tag


    pls = phone_lofter_spider(headers, cookies, tag, list_type, timelimit, blog_type)
    tag_data = pls.get_tag_data()   #tag页数据
    # print(len(tag_data))
    json.dump(tag_data, open("tag_data.json", "w", encoding="utf-8"), ensure_ascii=False, indent=4)
    #
    for bolg_info in tag_data:
        pls.get_blog_info(bolg_info)
