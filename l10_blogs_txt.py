import requests
import useragentutil
import re
import time
import random
import os
from lxml.html import etree
import parse_template
import l4_author_img
from l13_like_share_tag import filename_check


# 博客发表时间需要从归档页面获取，内容较长，所以单独分出一个方法
def get_time_and_title(blog_url, author_id):
    print("准备从归档页面获取时间", end="    ")
    author_url = blog_url.split("/post")[0]
    archive_url = author_url + "/dwr/call/plaincall/ArchiveBean.getArchivePostByTime.dwr"
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
        open("blog.txt", "w", encoding="utf-8").write(page_data)

        try:
            next_param2 = 'number:' + str(re.search('s%d\.time=(.*);s.*type' % (50 - 1), page_data).group(1))
            data['c0-param2'] = next_param2
        except AttributeError:
            # 仅自己可见的在归档页没有，会一直翻到最后都不break，最后一页没有50条上面的re匹配会超
            break
        time.sleep(random.randint(1, 2))
    if not the_blog_info:
        print("未能从归档页中获取时间与标题")
        return ["", ""]
    # 用正则匹配出标题和时间戳并格式化
    timestamp = re.search(r's[\d]*.time=(\d*);', the_blog_info).group(1)
    public_time = time.strftime("%Y-%m-%d", time.localtime(int(int(timestamp) / 1000)))
    re_title = re.findall(r'[\d]*.title="(.*?)"', the_blog_info)
    if re_title:
        # 文章会匹配到标题,文本的中间也有空字符串['']
        title = re_title[0]
        title = title.encode('latin-1').decode('unicode_escape')
    else:
        # 图片配文没有 title=这一项
        title = f"图片配文 {public_time}"
    if public_time:
        print("已获取到时间")
    else:
        print("未获取到博客 %s 的发布时间" % blog_url)

    return [public_time, title]


# 解析博客页面，返回图片信息
def save_files(blogs_urls, login_key, login_auth):
    global pre_page_last_img_info
    imgs_info = []
    blog_num = 0
    blen = len(blogs_urls)
    # 循环len(blogs_info)次，每次解析blogs_info的第一元素，解析完后删除
    for blog_url in blogs_urls:
        print("博客 %s 开始解析" % (blog_url))
        author_ip = re.search(r"http(s)*://(.*).lofter.com/", blog_url).group(2)

        blog_html = requests.get(blog_url, headers=useragentutil.get_headers(),
                                 cookies={login_key: login_auth}).content.decode("utf-8")
        blog_parse = etree.HTML(blog_html)

        author_view_url = blog_url.split("/post")[0] + "/view"
        author_view_parse = etree.HTML(
            requests.get(author_view_url, cookies={login_key: login_auth}).content.decode("utf-8"))
        author_id = author_view_parse.xpath("//body//iframe[@id='control_frame']/@src")[0].split("blogId=")[1]
        author_name = author_view_parse.xpath("//h1/a/text()")[0]

        time_and_title = get_time_and_title(blog_url, author_id)
        public_time = time_and_title[0]
        title = time_and_title[1]
        if not public_time and not title:
            # 只not标题可能是文本，两都没有才是匹配大失败
            print("尝试从博客页中匹配标题", end="\t")
            title_path = blog_parse.xpath("//h2//text()")
            if title_path:
                title = title_path[0]
                print("匹配成功", title)
            else:
                print("匹配失败，将作为文本保存")

            print("尝试从博客页中匹配发表时间", end="\t")
            re_date = re.search("\d{4}[.\\\/-]\d{2}[.\\\/-]\d{2}", blog_html)
            if re_date:
                public_time = re_date.group(0).replace("\\", "-").replace(".", "-").replace("/", "-")
                print("匹配成功", public_time)
            else:
                public_time = "1970-01-01"
                print("匹配失败，发表时间将设为 1970-01-01")

        blog_type = "article" if title else "text"
        article_head = "{} by {}[{}]\n发表时间：{}".format(title, author_name, author_ip,
                                                      public_time) + "\n" + "原文链接： " + blog_url
        if title:
            file_name = title + " by " + author_name + ".txt"
        else:
            file_name = author_name + " " + public_time + ".txt"
        file_name = file_name.replace("/", "&").replace("|", "&").replace("\\", "&").replace("<", "《") \
            .replace(">", "》").replace(":", "：").replace('"', '”').replace("?", "？").replace("*", "·"). \
            replace("\n", "").replace("(", "（").replace(
            ")", "）")
        print("准备保存：{} ，原文连接： {} ".format(file_name, blog_url))
        template_id = parse_template.matcher(blog_parse)
        print("文字匹配模板为模板{}".format(template_id))
        if template_id == 0:
            print("文字匹配模板是根据作者主页自动匹配的，模板0为通用匹配模板，除了文章主体之外可能会爬到一些其他的内容，也有可能出现文章部分内容缺失")
        article_content = parse_template.get_content(blog_parse, template_id, title, blog_type)
        article = article_head + "\n\n\n\n" + article_content

        file_path = "./dir/article/this"
        file_name = filename_check(file_name, article, file_path, "txt")
        with open("{}/{}".format(file_path, file_name), "w", encoding="utf-8") as op:
            op.write(article)
        print("{}  保存完成\n".format(file_name, author_name))


if __name__ == '__main__':
    from login_info import login_auth, login_key

    # 启动程序前请先填写 login_info.py
    # 不用改代码，把链接写到./dir/txt_list里，一行一个链接，再运行这个程序，会一个一个下

    # 记录个问题(只是记给我自己看的，看不明白可以不管)
    # 仅自己可见的内容在归档里看不见，没办法拿发表时间戳
    # 用了正则从博客页匹配，不过有的模板不显示完整时间，所以还是拿不到，以及有可能匹配到评论发表的时间
    # \d{4}[.\\\/-]\d{2}[.\\\/-]\d{2}

    path = "./dir/article"
    arthicle_path = "./dir/article/this"
    for x in [path, arthicle_path]:
        if not os.path.exists(x):
            os.makedirs(x)

    with open("./dir/txt_list") as op:
        blog_urls = op.readlines()
    blog_urls = list(map(lambda x: x.replace("\n", ""), blog_urls))
    archives_info = save_files(blog_urls, login_key, login_auth)
