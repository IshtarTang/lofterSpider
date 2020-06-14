import re
import os
import time
import random
import requests
from lxml.html import etree
import useragentutil
import parse_template
import l4_author_img

session = requests.session()


def get_parse(url):
    content = requests.get(url, headers=useragentutil.get_headers()).content
    parse = etree.HTML(content)
    return parse


def title_filter(title, target_titles):
    for target_title in target_titles:
        if target_title in title:
            return 1
    return 0


def chapter_format(target_titles, blogs_info):
    chapter_infos = {}
    # 以title为key的字典，值为该标题下章节的信息
    for target_title in target_titles:
        chapter_infos[target_title] = []
    # 加入信息
    for blog_info in blogs_info:
        for target_title in target_titles:
            if target_title in blog_info["title"]:
                chapter_infos[target_title].append(blog_info)
    # 由于爬虫的顺序是从后wan
    for target_title in target_titles:
        chapter_infos[target_title] = chapter_infos[target_title][::-1]
    return chapter_infos


def parse_archive_page(url, header, data, author_url, query_num, start_time, end_time, target_titles, merger_chapter):
    all_blog_info = []

    while True:
        print("获取归档页面信息，当前请求的时间戳参数为 %s" % data["c0-param2"])
        page_data = l4_author_img.post_content(url=url, data=data, head=header)
        # 正则匹配出每条博客的信息并增加到数组all_blog_info
        # new_blogs_info = re.findall(r"s[\d]*.blogId.*\n.*noticeLinkTitle", page_data)
        new_blogs_info = re.findall(r"s[\d]*.blogId.*\n.*\n", page_data)
        all_blog_info += new_blogs_info
        # 当返回的博客数不等于请求参数中的query_num时说明已经获取到所有的博客信息，跳出循环
        if not len(new_blogs_info) == query_num:
            break
        # 如果设定了开始时间，且最后一个时间戳小于设定的时间，跳出循环
        if start_time:
            if l4_author_img.is_stamp_early(data["c0-param2"].split(":")[1], start_time):
                break
        # 正则匹配本页最后一条博客信息的时间戳，用于下个请求data中的参数
        data['c0-param2'] = 'number:' + str(re.search('s%d\.time=(.*);s.*type' % (query_num - 1), page_data).group(1))
        time.sleep(random.randint(1, 2))

    # 过滤和整理博客信息，整理后每条结构为{"url": "http://***","time": "20**-**-**","img_url": "http://***"}
    parsed_blog_info = []
    blog_num = 0
    for blog_info in all_blog_info:
        # 时间戳
        timestamp = re.search(r's[\d]*.time=(\d*);', blog_info).group(1)
        # 只爬取设定时间内，时间线时从新到旧，如果早于该时间则直接跳出循环，如果晚于则跳过这一次循环，没有设定则全部爬取。
        if start_time:
            if l4_author_img.is_stamp_early(timestamp, start_time):
                break
        if end_time:
            if l4_author_img.is_stamp_late(timestamp, end_time):
                continue
        blog_info_dic = {}
        blog_num += 1

        # 获取缩略图链接，过滤没有图片的博客链接
        try:
            title = re.findall(r'[\d]*.title="(.*?)"', blog_info)[0]
            blog_info_dic["title"] = title.encode('latin-1').decode('unicode_escape')
        except:
            blog_info_dic["title"] = ""
        if not blog_info_dic["title"]:
            continue

        # 博客的编号 比如https://lindujiu.lofter.com/post/423a9c_1c878d5e6 的 423a9c_1c878d5e6
        blog_index = re.search(r's[\d]*.permalink="(.*?)";', blog_info).group(1)
        blog_info_dic["url"] = author_url + "post/" + blog_index

        # 获取时间
        # time_local = time.localtime(int(timestamp) / 1000)
        time_local = time.localtime(int(int(timestamp) / 1000))
        dt_time = time.strftime("%Y-%m-%d", time_local)
        # public_time = time.strftime("%Y-%m-%d", time.localtime(int(int(timestamp) / 1000)))
        blog_info_dic["time"] = dt_time

        parsed_blog_info.append(blog_info_dic)

    print("归档页面解析完毕，共获取博客链接数%d，带标题博客数%d" % (blog_num, len(parsed_blog_info)))
    if not target_titles:
        return parsed_blog_info
    else:
        filterd_blog_infos = []
        print("开始进行标题过滤")
        for blog_info in parsed_blog_info:
            if title_filter(blog_info["title"], target_titles):
                print("文章 {} 保留".format(blog_info["title"]))
                filterd_blog_infos.append(blog_info)
            else:
                print("文章 {} 被过滤掉".format(blog_info["title"]))
    print("\n过滤后剩余文章 {} 篇\n".format(len(filterd_blog_infos)))
    if not merger_chapter:

        return filterd_blog_infos
    else:
        print("开始整理章节")
        chapter_infos = chapter_format(target_titles, filterd_blog_infos)
        print("整理完成")
        for target_title in target_titles:
            print("获取到 {} 共{}章".format(target_title, len(chapter_infos[target_title])))
        print()
        return chapter_infos


def save_file(blog_infos, author_name, author_ip):
    print("开始保存文章内容")
    first_parse = get_parse(blog_infos[0]["url"])
    first_title = blog_infos[0]["title"]
    template_id = parse_template.matcher(first_parse, first_title)
    print("文字匹配模板为模板{}".format(template_id))
    if template_id == 0:
        print("文字匹配模板是根据作者主页自动匹配的，模板0是一个匹配度比较广的模板，使用模板0说明没有其他的模板匹配成功，除了文章主体之外可能会爬到一些其他的内容，也有可能出现文章部分内容缺失")
        str = input("输入ok确定继续爬取，或输入任意其他文字退出\n")
        if not str == "ok":
            print("退出")
            exit()
    arthicle_path = "./dir/article/{}".format(author_name)

    for blog_info in blog_infos:
        title = blog_info["title"]
        public_time = blog_info["time"]
        url = blog_info["url"]
        print("准备保存：{} by {}，原文连接： {} ".format(title, author_name, url), end="    ")
        file_name = "{} by {}".format(title, author_name)
        article_head = "{} by {}[{}]\n发表时间：{}\n原文链接： {}".format(title, author_name, author_ip, public_time, url)
        parse = get_parse(url)
        article_content = parse_template.get_content(parse, template_id, title) \
            .replace("                            ", "")
        article = article_head + "\n" + article_content
        with open(arthicle_path + "/" + file_name + ".txt", "w", encoding="utf-8") as op:
            op.write(article)
        print("{} by {} 保存完毕".format(title, author_name))


def save_chapter(article_infos, target_titles, author_name, author_ip):
    print("准备开始保存文章")
    arthicle_path = "./dir/article/{}".format(author_name)
    test_info = article_infos[target_titles[0]][0]
    test_parse = get_parse(test_info["url"])
    test_title = test_info["title"]
    template_id = parse_template.matcher(test_parse, test_title)
    print("文字匹配模板为模板{}".format(template_id))
    if template_id == 0:
        print("文字匹配模板是根据作者主页自动匹配的，模板0是一个匹配度比较广的模板，使用模板0说明没有其他的模板匹配成功，除了文章主体之外可能会爬到一些其他的内容，也有可能出现文章部分内容缺失")
        str = input("输入ok确定继续爬取，或输入任意其他文字退出\n")
        if not str == "ok":
            exit()

    for target_title in target_titles:
        chapters_info = article_infos[target_title]
        print("开始保存 {}，第一章节链接 {}".format(target_title, chapters_info[0]["url"]))
        file_name = target_title + " by " + author_name
        article_head = file_name + "[" + author_ip + "]\n第一章节发表时间：{}".format(
            chapters_info[0]["time"]) + "\n最后章节发表时间：{}".format(chapters_info[-1]["time"]) + "\n\n"
        article_content = article_head
        num = 1
        for chapter_info in chapters_info:
            chapter_parse = get_parse(chapter_info["url"])
            chapter_content = "\n第{}章\n".format(num) + parse_template.get_content(chapter_parse, template_id,
                                                                                  chapter_info["title"]) + "\n\n"
            chapter_content = chapter_content.replace("                              ", "")
            article_content += chapter_content
            print("保存进度{}/{}".format(num, len(chapters_info)))
            num += 1

        with open(arthicle_path + "/" + file_name + ".txt", "w", encoding="utf-8") as op:
            op.write(article_content)
        print("{} 保存完成\n".format(target_title))


def run(author_url, start_time, end_time, target_titles, merger_chapter):
    author_page_parse = etree.HTML(
        requests.get(author_url, headers=useragentutil.get_headers()).content.decode("utf-8"))
    # id是是获取归档页面需要的一个参数，纯数字；ip是作者在lofter的三级域名，由作者注册时设定
    author_id = author_page_parse.xpath("//body/iframe[@id='control_frame']/@src")[0].split("blogId=")[1]
    author_ip = re.search(r"http[s]*://(.*).lofter.com/", author_url).group(1)

    try:
        author_name = author_page_parse.xpath("//title//text()")[0]
    except:
        author_name = input("解析作者名时出现异常，请手动输入\n")
    archive_url = author_url + "dwr/call/plaincall/ArchiveBean.getArchivePostByTime.dwr"

    query_num = 50
    data = l4_author_img.make_data(author_id, query_num)
    head = l4_author_img.make_head(author_url)

    print("作者名%s,lofterip%s,主页链接 %s" % (author_name, author_ip, author_url))
    path = "./dir/article"
    arthicle_path = "./dir/article/{}".format(author_name)
    for x in [path, arthicle_path]:
        if not os.path.exists(x):
            os.makedirs(x)

    blog_infos = parse_archive_page(archive_url, head, data, author_url, query_num, start_time, end_time, target_titles,
                                    merger_chapter)
    if target_titles and merger_chapter:
        save_chapter(blog_infos, target_titles, author_name, author_ip)

    else:
        save_file(blog_infos, author_name, author_ip)
        # print("end")
    print("运行结束")


if __name__ == '__main__':
    # 作者的主页地址   示例 https://tang0396.lofter.com/   *最后的'/'不能少
    author_url = "http://canggoucelia.lofter.com/"

    # ### 自定义部分 ### #

    # 设定爬取哪个时间段的博客，空值为不设定 格式："yyyy-MM-dd"
    start_time = "2019-01-01"
    end_time = ""

    # 文章标题指定：只爬取标题标题包含指定内容的文章，适用于爬取系列文或多章节文章，空值为不指定。
    target_titles = []
    # 章节合并：指定文章标题时该功能生效，开启后爬取多章节文章时会按标题自动合并文章。0为关闭，1为启动。
    # 注意，如果开启章节合并，文件名会使用你在标题指定中写的名称
    merger_chapter = 1

    run(author_url, start_time, end_time, target_titles, merger_chapter)
