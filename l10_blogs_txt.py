import requests
import useragentutil
import re
import time
import random
import os
from lxml.html import etree
import l8_blogs_img
import parse_template
import l4_author_img


def get_parse(url):
    content = requests.get(url, headers=useragentutil.get_headers()).content
    parse = etree.HTML(content)
    return parse


# 博客发表时间需要从归档页面获取，内容较长，所以单独分出一个方法
def get_time_and_title(blog_url, author_page_parse):
    print("准备从归档页面获取时间", end="    ")
    public_time = ""
    author_url = blog_url.split("/post")[0]
    archive_url = author_url + "/dwr/call/plaincall/ArchiveBean.getArchivePostByTime.dwr"
    author_id = author_page_parse.xpath("//body/iframe[@id='control_frame']/@src")[0].split("blogId=")[1]
    data = l4_author_img.make_data(author_id, 50)
    header = l4_author_img.make_head(author_url)
    blog_id = blog_url.split("/")[-1]
    flag = False
    the_blog_info = ""
    while True:
        page_data = l4_author_img.post_content(url=archive_url, data=data, head=header)
        # 正则匹配出每条博客的信息
        blogs_info = re.findall(r"s[\d]*.blogId.*\n.*\n", page_data)
        # 循环每条，找到匹配的信息
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

    # 用正则匹配出标题和时间戳并格式化
    timestamp = re.search(r's[\d]*.time=(\d*);', the_blog_info).group(1)
    public_time = time.strftime("%Y-%m-%d", time.localtime(int(int(timestamp) / 1000)))
    title = re.findall(r'[\d]*.title="(.*?)"', the_blog_info)[0]
    title = title.encode('latin-1').decode('unicode_escape')
    if public_time:
        print("已获取到时间")
    else:
        print("未获取到博客 %s 的发布时间" % blog_url)
    if title:
        print("获取到标题{}".format(title))
    return [public_time, title]


# 解析博客页面，返回图片信息
def save_files(blogs_urls):
    global pre_page_last_img_info
    imgs_info = []
    blog_num = 0
    blen = len(blogs_urls)
    # 循环len(blogs_info)次，每次解析blogs_info的第一元素，解析完后删除
    for blog_url in blogs_urls:
        print("博客 %s 开始解析" % (blog_url))
        author_page_parse = etree.HTML(requests.get(blog_url.split("/post")[0]).content.decode("utf-8"))
        author_name = author_page_parse.xpath("//title/text()")[0].replace("\n", "").replace(" ", "")
        author_ip = re.search(r"http(s)*://(.*).lofter.com/", blog_url).group(2)
        parse = get_parse(blog_url)
        time_and_title = get_time_and_title(blog_url, author_page_parse)
        title = time_and_title[1]
        article_head = "{} by {}[{}]\n发表时间：{}".format(title, author_name, author_ip, time_and_title[0])+"\n"+"原文链接： "+blog_url
        file_name = title + " by " + author_name + ".txt"
        file_name = file_name.replace("/", "&").replace("|", "&").replace("\\", "&").replace("<", "《") \
            .replace(">", "》").replace(":", "：").replace('"', '”').replace("?", "？").replace("*", "·"). \
            replace("\n", "").replace("(", "（").replace(
            ")", "）")
        print("准备保存：{} by {}，原文连接： {} ".format(title, author_name, blog_url))
        template_id = parse_template.matcher(parse)
        print("文字匹配模板为模板{}".format(template_id))
        if template_id == 0:
            print("文字匹配模板是根据作者主页自动匹配的，模板0为通用匹配模板，除了文章主体之外可能会爬到一些其他的内容，也有可能出现文章部分内容缺失")
        article_content = parse_template.get_content(parse, template_id, title)
        article = article_head + "\n\n\n\n" + article_content
        with open("./dir/article/this/{}".format(file_name), "w", encoding="utf-8") as op:
            op.write(article)
        print("{} by {} 保存完成\n".format(title, author_name))


if __name__ == '__main__':
    path = "./dir/article"
    arthicle_path = "./dir/article/this"
    for x in [path, arthicle_path]:
        if not os.path.exists(x):
            os.makedirs(x)

    with open("./dir/txt_list") as op:
        blog_urls = op.readlines()
    blog_urls = list(map(lambda x: x.replace("\n", ""), blog_urls))
    archives_info = save_files(blog_urls)
