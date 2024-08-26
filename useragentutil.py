# coding:utf-8
import random

# 本来是随机获取请求头用的，但是现在所有页面都要登录，这玩意就没效果了，只留一个
user_agent_datas = [
    {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36'}
]


def get_headers():
    index = random.randint(0, len(user_agent_datas) - 1)
    return user_agent_datas[index]


if __name__ == '__main__':
    print("随机获得值为:", get_headers())
