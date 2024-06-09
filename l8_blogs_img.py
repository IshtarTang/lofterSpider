import requests
import useragentutil
import re
import time
import os
import random
from lxml.html import etree
import l4_author_img


# 博客发表时间需要从归档页面获取，内容较长，所以单独分出一个方法
def get_time(blog_url, author_id, login_key, login_auth):
    print("准备从归档页面获取时间", end="    ")
    author_url = blog_url.split("/post")[0]
    archive_url = author_url + "/dwr/call/plaincall/ArchiveBean.getArchivePostByTime.dwr"
    data = l4_author_img.make_data(author_id, 50)
    header = l4_author_img.make_head(author_url)
    blog_id = blog_url.split("/")[-1]
    flag = False
    the_blog_info = ""
    while True:
        page_data = l4_author_img.post_content(url=archive_url, data=data, head=header,
                                               cookies_dict={login_key: login_auth})
        # 正则匹配出每条博客的信息
        blogs_info = re.findall(r"s[\d]*.blogId.*\n.*noticeLinkTitle", page_data)
        # 循环每条信息
        for blog_info in blogs_info:
            if blog_id in blog_info:
                the_blog_info = blog_info
                flag = True
                break
        if flag:
            break
        # # 当返回的博客数不等于请求参数中的query_num时说明已经获取到所有的博客信息，跳出循环
        # if not len(blogs_info) == 50:
        #     break
        # 正则匹配本页最后一条博客信息的时间戳，用于下个请求data中的参数
        data['c0-param2'] = 'number:' + str(
            re.search('s%d\.time=(.*);s.*type' % (50 - 1), page_data).group(1))
        time.sleep(random.randint(1, 2))

    # 找到匹配的信息，用正则匹配出时间戳并格式化
    timestamp = re.search(r's[\d]*.time=(\d*);', the_blog_info).group(1)
    public_time = time.strftime("%Y-%m-%d", time.localtime(int(int(timestamp) / 1000)))

    if public_time:
        print("已获取到时间")
    else:
        print("未获取到博客 %s 的发布时间" % blog_url)
    return public_time


# 解析博客页面，返回图片信息
def parse_blogs_info(blogs_urls, login_key, login_auth):
    global pre_page_last_img_info
    imgs_info = []
    blog_num = 0
    blen = len(blogs_urls)
    # 循环len(blogs_info)次，每次解析blogs_info的第一元素，解析完后删除
    for blog_url in blogs_urls:
        print("博客 %s 开始解析" % (blog_url))
        content = requests.get(blog_url, headers=useragentutil.get_headers()).content.decode("utf-8")
        author_view_url = blog_url.split("/post")[0] + "/view"
        author_view_parse = etree.HTML(
            requests.get(author_view_url, cookies={login_key: login_auth}).content.decode("utf-8"))
        author_name = author_view_parse.xpath("//h1/a/text()")[0]
        author_id = author_view_parse.xpath("//body//iframe[@id='control_frame']/@src")[0].split("blogId=")[1]
        author_ip = re.search(r"http(s)*://(.*).lofter.com/", blog_url).group(2)
        # 获取博客发表时间
        public_time = get_time(blog_url, author_id, login_key, login_auth)

        # 不同作者主页会有不同页面结构，所以没有使用xpath而是直接用正则匹配出所有的图片链接
        # imgs_url = re.findall('"(http[s]{0,1}://imglf\d{0,1}.nosdn\d*.[0-9]{0,3}.net.*?)"', content)
        imgs_url = re.findall('"(http[s]{0,1}://imglf\d{0,1}.lf\d*.[0-9]{0,3}.net.*?)"', content)

        # 图片文件下标接上次的增加
        img_index = 0
        blog_num += 1

        # 过滤博客页面中获取到的图片链接
        imgs_url = l4_author_img.img_fliter(imgs_url, "img")
        print(imgs_url)

        # 整理图片信息，用于下一步保存
        for img_url in imgs_url:
            img_index += 1
            # 判断图片类型
            is_gif = re.findall("gif", img_url)
            is_png = re.findall("png", img_url)
            if is_gif:
                img_type = "gif"
            elif is_png:
                img_type = "png"
            else:
                img_type = "jpg"
            img_info = {}
            img_info["img_url"] = img_url
            author_name_in_filename = author_name.replace("/", "&").replace("|", "&").replace("\\", "&"). \
                replace("<", "《").replace(">", "》").replace(":", "：").replace('"', '”').replace("?", "？"). \
                replace("*", "·").replace("\n", "").replace("(", "（").replace(")", "）")
            img_info["pic_name"] = author_name_in_filename + "[" + author_ip + "] " + public_time + "(" + str(
                img_index) + ")." + img_type
            imgs_info.append(img_info)
            # 这里想遇到png的时候存一张png格式，一张jpg格式。png格式有透明图层有的要在jpg格式下才能看全
            # 但总之效果不好所以弃用
            # if img_type == "png":
            #     img_info_2={}
            #     img_info_2["img_url"] = img_url
            #     img_info_2["pic_name"] = author_name + "[" + author_ip + "] " + public_time + "(" + str(
            #         img_index) + ").jpg"
            #     imgs_info.append(img_info_2)

        blen -= 1
        print("解析完成，获取到图片链接%d，总获取图片数%d，已解析完成%d个链接，剩余%d" % (len(imgs_url), len(imgs_info), blog_num, blen))
        print()
    return imgs_info


def download_img(imgs_info):
    dir_path = "./dir/img/this"
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    num = 0
    list_len = len(imgs_info)
    for img_info in imgs_info:
        pic_name = img_info["pic_name"]
        pic_url = img_info["img_url"]
        img_path = dir_path + "/" + pic_name
        print("获取图片 %s，%s" % (pic_url, pic_name))
        content = requests.get(pic_url, headers=useragentutil.get_headers()).content
        with open(img_path, "wb") as op:
            op.write(content)
        num += 1
        list_len -= 1
        print("图片已保存，共保存图片%d ，余%d" % (num, list_len))

        if num % 8 == 0:
            time.sleep(1)


if __name__ == '__main__':
    from login_info import login_auth, login_key

    # 启动程序前请先填写 login_info.py
    with open("./dir/img_list") as op:
        blog_urls = op.readlines()
    blog_urls = list(map(lambda x: x.replace("\n", ""), blog_urls))
    imgs_info = parse_blogs_info(blog_urls, login_key, login_auth)
    download_img(imgs_info)
