import requests
from lxml.html import etree
from login_info import login_auth, login_key
import re
import time


def homepage_extract(homepage_url, page):
    cookies = {
        login_key: login_auth,
    }

    headers = {
        'Host': re.match("https://(.*?)/", url).group(1),
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0',
        'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-User': '?1',
        'Sec-Fetch-Dest': 'document',
        'Referer': homepage_url,
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh-TW;q=0.9,zh;q=0.8,en;q=0.7',
    }

    params = (
        ('page', str(page)),
    )

    response = requests.get(homepage_url, headers=headers, params=params, cookies=cookies)
    html = response.content.decode("utf-8")
    parse = etree.HTML(html)
    links = parse.xpath("//div[contains(@class,'postwrapper')]/div//div[@class='day']/a/@href")
    return links


if __name__ == '__main__':
    # 扫描主页，能扫到仅自己可见的
    # 把所有博客链接拿下来存到links.txt，仅支持lofter默认模板（灰色良品）
    # 这个程序算l8和l10的配件吧

    # 启动程序前需先填写 login_info.py
    # 主页链接，最后的'/'不能少
    url = 'https://loftercreator.lofter.com/'

    page = 1
    all_links = []
    while True:
        links = homepage_extract(url, page)
        if links:
            print(f"page {page} 链接数 {len(links)}")
            all_links += links
            page += 1
            time.sleep(1.5)
        else:
            break
    print(len(all_links))
    print(len(set(all_links)))
    with open("links.txt", "w", encoding="utf-8") as op:
        for link in all_links:
            op.write(link)
            op.write("\n")
