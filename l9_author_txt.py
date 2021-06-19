import re
import os
import time
import random
import requests
from lxml.html import etree
import useragentutil
import parse_template
import l4_author_img
import l13_like_share_tag

session = requests.session()


def get_parse(url):
    content = requests.get(url, headers=useragentutil.get_headers()).content
    parse = etree.HTML(content)
    return parse


def parse_archive_page(url, header, data, author_url, author_name, query_num, start_time, end_time):
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

        # 获取标题
        title = ""
        # 获取标题，纯文本博客会获取一个空标题，图片博客没有标题
        re_title = re.findall(r'[\d]*\.title="(.*?)"', blog_info)
        re_content = re.findall(r'[\d]*\.content="(.*?)"', blog_info)
        # 这个判断总觉得有点问题
        if re_title and re_title[0]:
            title = re_title[0].encode('latin-1').decode('unicode_escape')
            blog_info_dic["blog_type"] = "article"
        elif re_content:
            # 没有标题的纯文本信息，先弄一个临时title
            title = "tmp_title"
            blog_info_dic["blog_type"] = "text"

        # 没有title就直接跳过后面的解析
        if not title:
            continue

        # 博客的编号 比如https://lindujiu.lofter.com/post/423a9c_1c878d5e6 的 423a9c_1c878d5e6
        blog_index = re.search(r's[\d]*.permalink="(.*?)";', blog_info).group(1)
        blog_info_dic["url"] = author_url + "post/" + blog_index

        # 获取时间
        time_local = time.localtime(int(int(timestamp) / 1000))
        dt_time = time.strftime("%Y-%m-%d", time_local)
        # public_time = time.strftime("%Y-%m-%d", time.localtime(int(int(timestamp) / 1000)))
        blog_info_dic["time"] = dt_time
        if blog_info_dic["blog_type"] == "text":
            title = "{} {}".format(author_name, dt_time)
        blog_info_dic["title"] = title
        blog_info_dic["print_title"] = blog_info_dic["title"].encode("gbk", errors="replace").decode("gbk",

                                                                                                     errors="replace")

        parsed_blog_info.append(blog_info_dic)

    print("归档页面解析完毕，共获取博客链接数%d，文本与文章篇数%d" % (blog_num, len(parsed_blog_info)))
    return parsed_blog_info


def save_file(blog_infos, author_name, author_ip):
    print("开始保存文章内容")
    # 拿一篇出来，测试匹配模板
    first_parse = get_parse(blog_infos[0]["url"])
    template_id = parse_template.matcher(first_parse)
    print("文字匹配模板为模板{}".format(template_id))
    if template_id == 0:
        print("文字匹配模板是根据作者主页自动匹配的，模板0是一个匹配度比较广的模板，使用模板0说明没有其他的模板匹配成功，除了文章主体之外可能会爬到一些其他的内容，也有可能出现文章部分内容缺失")
        input1 = input("输入ok确定继续爬取，或输入任意其他文字退出\n")
        if not input1 == "ok":
            print("退出")
            exit()
    # 开始保存

    arthicle_path = "./dir/article/{}".format(author_name)
    for blog_info in blog_infos:
        # 信息提取
        title = blog_info["title"]
        print_title = blog_info["print_title"]
        public_time = blog_info["time"]
        url = blog_info["url"]
        blog_type = blog_info["blog_type"]
        print("准备保存：{} ，原文连接： {} ".format(print_title, url), end="    ")

        # 文件头
        if blog_info["blog_type"] == "article":
            article_head = "{} by {}[{}]\n发表时间：{}\n原文链接： {}".format(title, author_name, author_ip, public_time, url)
        else:
            article_head = "{}[{}]\n原文链接： {}".format(title, author_ip, url)
        # 正文
        parse = get_parse(url)
        article_content = parse_template.get_content(parse, template_id, title, blog_type)

        # 文件尾，文章中插的图片
        # 匹配新格式
        img_src = parse.xpath("//img/@src")
        tmp_str = "\n".join(img_src)
        illustration = re.findall('(http[s]{0,1}://imglf\d{0,1}.lf\d*.[0-9]{0,3}.net.*?)\?', tmp_str)
        if illustration == []:
            # 匹配旧格式
            illustration = re.findall('"(http[s]{0,1}://imglf\d{0,1}.nosdn\d*.[0-9]{0,3}.net.*?)\?',
                                      "\n".join(img_src))
        if illustration:
            article_tail = "博客中包含的图片：\n" + "\n".join(illustration)
        else:
            article_tail = ""

        # 全文
        article = article_head + "\n\n\n\n" + article_content + "\n\n\n" + article_tail
        article = article.encode("utf-8", errors="replace").decode("utf-8", errors="replace")

        # 文件名
        if blog_info["blog_type"] == "article":
            # 文章用 文章名by作者，替换掉非法字符
            file_name = "{} by {}.txt".format(title, author_name)
            file_name = file_name.replace("/", "&").replace("|", "&").replace("\\", "&").replace("<", "《") \
                .replace(">", "》").replace(":", "：").replace('"', '”').replace("?", "？").replace("*", "·"). \
                replace("\n", "").replace("(", "（").replace(
                ")", "）")
        else:
            # 文本要检查是否重名
            file_name = l13_like_share_tag.filename_check(title + ".txt", article, arthicle_path, "txt")

        # 写入
        with open(arthicle_path + "/" + file_name, "w", encoding="utf-8") as op:
            op.write(article)
        print("{}  保存完毕".format(file_name))


def run(author_url, start_time, end_time):
    author_page_parse = etree.HTML(
        requests.get(author_url, headers=useragentutil.get_headers()).content.decode("utf-8"))
    # id是是获取归档页面需要的一个参数，纯数字；ip是作者在lofter的三级域名，由作者注册时设定
    author_id = author_page_parse.xpath("//body/iframe[@id='control_frame']/@src")[0].split("blogId=")[1]
    author_ip = re.search(r"http[s]*://(.*).lofter.com/", author_url).group(1)

    try:
        author_name = author_page_parse.xpath("//title//text()")[0]
    except:
        author_name = input("解析作者名时出现异常，请手动输入\n")
    # 归档页链接
    archive_url = author_url + "dwr/call/plaincall/ArchiveBean.getArchivePostByTime.dwr"

    query_num = 50
    data = l4_author_img.make_data(author_id, query_num)
    head = l4_author_img.make_head(author_url)

    print("作者名%s,lofter ip %s,主页链接 %s" % (author_name, author_ip, author_url))
    path = "./dir/article"
    arthicle_path = "./dir/article/{}".format(author_name)

    # 博客信息爬取
    blog_infos = parse_archive_page(archive_url, head, data, author_url, author_name, query_num, start_time, end_time)

    if not blog_infos:
        print("作者主页中无文本/文字博客，无需爬取，程序退出")
        exit()

    for x in [path, arthicle_path]:
        if not os.path.exists(x):
            os.makedirs(x)

    save_file(blog_infos, author_name, author_ip)
    # print("end")
    print("运行结束")


if __name__ == '__main__':
    # 作者的主页地址   示例 https://ishtartang.lofter.com/   *最后的'/'不能少
    author_url = "https://lofterxms.lofter.com/"

    # ### 自定义部分 ### #

    # 设定爬取哪个时间段的博客，空值为不设定 格式："yyyy-MM-dd"
    start_time = ""
    end_time = ""

    run(author_url, start_time, end_time)
