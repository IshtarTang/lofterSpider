import re
import os
import shutil
import time
import random
import requests
from lxml.html import etree
import useragentutil
import parse_template
import l4_author_img
import l13_like_share_tag
import numpy as np
from collections import Counter


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

        # 博客的编号 比如https://lindujiu.lofter.com/post/423a9c_1c878d5e6 的 423a9c_1c878d5e6
        blog_index = re.search(r's[\d]*.permalink="(.*?)";', blog_info).group(1)
        blog_info_dic["url"] = author_url + "post/" + blog_index

        # 获取标题
        title = ""
        # 获取标题，纯文本博客会获取一个空标题，图片博客没有标题，确认文本有效后弄个临时标题（这里的文本内容并不会用到后面）
        re_title = re.findall(r'[\d]*\.title="(.*?)";', blog_info)
        re_content = re.findall(r'[\d]*\.content="(.*?)";', blog_info)
        # 这个判断总觉得有点问题
        if re_title and re_title[0]:
            title = re_title[0].encode('latin-1').decode('unicode_escape')
            blog_info_dic["blog_type"] = "article"
        elif re_content:
            # 没有标题的纯文本信息，先弄一个临时title
            blog_info_dic["blog_type"] = "text"
            title = "tmp_title"
        else:
            # 没有title就直接跳过后面的解析
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


def save_file(blog_infos, author_name, author_ip, get_comm, additional_break):
    all_file_name = []
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
            article_head = "{}\n原文链接： {}".format(title, url)
        # 正文
        content = requests.get(url, headers=useragentutil.get_headers()).content
        parse = etree.HTML(content)
        join_word = "\n" * additional_break
        article_content = parse_template.get_content(parse, template_id, title, blog_type, join_word)
        comm_list = []
        # 评论
        if get_comm:
            referer_url = parse.xpath("//iframe[@id='comment_frame']/@src")[0]
            param0 = re.search("pid=(\d+)&bid=", referer_url).group(1)
            number1 = 50
            number2 = 0
            comm_url = "https://www.lofter.com/dwr/call/plaincall/PostBean.getPostResponses.dwr"
            headers = {
                'Host': 'www.lofter.com',
                'Origin': 'https://www.lofter.com',
                'Referer': "https:" + referer_url,
                'Accept-Encoding': 'gzip, deflate',
            }
            all_comm_str = ""
            while True:
                comm_data = {"callCount": "1",
                             "scriptSessionId": "${scriptSessionId}187",
                             "httpSessionId": "",
                             "c0-scriptName": "PostBean",
                             "c0-methodName": "getPostResponses",
                             "c0-id": "0",
                             "c0-param0": "number:{}".format(param0),
                             "c0-param1": "number:{}".format(number1),
                             "c0-param2": "number:{}".format(number2),
                             "batchId": "334950"}
                number2 += number1
                comm_response = requests.post(comm_url, data=comm_data, headers=headers)
                comm_text = comm_response.content.decode("utf-8")
                all_comm_str += comm_text
                comm_infos = comm_text.split("anonymousUser")[1:]
                if not comm_infos:
                    break

                for comm_info in comm_infos:
                    # 获取的信息里每条评论有个s\d+编号
                    comm_sid = re.search("(s\d+)\.appVersion", comm_info).group(1)
                    # 评论内容
                    comm_content = re.search(comm_sid + '\.content="(.*?)";', comm_info).group(1) \
                        .encode('utf8', errors="replace").decode('unicode_escape')
                    # 评论发表时间
                    comm_publish_time = re.search(comm_sid + '\.publishTime=(\d+);', comm_info).group(1)
                    public_time = time.strftime("%Y-%m-%d %H:%M", time.localtime(int(comm_publish_time) / 1000))

                    # 发表者信息
                    publisher_sid = re.search(comm_sid + "\.publisherMainBlogInfo=(.*?);", comm_info).group(1)
                    # 昵称
                    re_publisher_nickname = re.search(publisher_sid + '\.blogNickName="(.*?)";', comm_info)
                    if not re_publisher_nickname:
                        re_publisher_nickname = re.search(publisher_sid + '\.blogNickName="(.*?)";', all_comm_str)
                    publisher_nickname = re_publisher_nickname.group(1) \
                        .encode('utf8', errors="replace").decode('unicode_escape')
                    # 用户名
                    re_publisher_blogname = re.search(publisher_sid + '\.blogName="(.*?)";', comm_info)
                    if not re_publisher_blogname:
                        re_publisher_blogname = re.search(publisher_sid + '\.blogName="(.*?)";', all_comm_str)
                    publisher_blogname = re_publisher_blogname.group(1) \
                        .encode('utf8', errors="replace").decode('unicode_escape')

                    # 回复
                    reply_blogsid = re.search(comm_sid + "\.replyBlogInfo=(.*?);", comm_info).group(1)
                    if not reply_blogsid == "null":
                        re_reply_nickname = re.search(reply_blogsid + '\.blogNickName="(.*?)";', comm_info)
                        if not re_reply_nickname:
                            re_reply_nickname = re.search(reply_blogsid + '\.blogNickName="(.*?)";', all_comm_str)
                        reply_nickname = re_reply_nickname.group(1).encode('utf8', errors="replace").decode(
                            'unicode_escape')
                        re_reply_blogname = re.search(reply_blogsid + '\.blogName="(.*?)";', comm_info)
                        if not re_reply_blogname:
                            re_reply_blogname = re.search(reply_blogsid + '\.blogName="(.*?)";', all_comm_str)
                        reply_blogname = re_reply_blogname.group(1)
                    else:
                        reply_nickname = ""
                        reply_blogname = ""
                    if reply_nickname:
                        comm = "{} {}[{}] 回复 {}[{}]：{}".format(public_time, publisher_nickname, publisher_blogname,
                                                               reply_nickname, reply_blogname, comm_content)
                    else:
                        comm = "{}  {}[{}]：{}".format(public_time, publisher_nickname, publisher_blogname, comm_content)
                    comm_list.append(comm)
        comm_list = comm_list[::-1]
        # 文件尾，文章中插,的图片
        # 匹配新格式

        illustration = re.findall('"(http[s]{0,1}://imglf\d{0,1}.lf\d*.[0-9]{0,3}.net.*?)"', content.decode("utf-8"))

        # 过滤后为空说明没有获取到有效图片
        if not l4_author_img.img_fliter(illustration, blog_type):
            illustration = re.findall('"(http[s]{0,1}://imglf\d.nosdn\d*.[0-9]{0,3}\d.net.*?)"',
                                      content.decode("utf-8"))
        illustration = l4_author_img.img_fliter(illustration, blog_type)
        '''
        illustration = re.findall('(http[s]{0,1}://imglf\d{0,1}.lf\d*.[0-9]{0,3}.net.*?)\?', tmp_str)
        if illustration == []:
            # 匹配旧格式
            illustration = re.findall('"(http[s]{0,1}://imglf\d{0,1}.nosdn\d*.[0-9]{0,3}.net.*?)\?',
                                      "\n".join(img_src))
        '''
        if illustration:
            article_tail = "博客中包含的图片：\n" + "\n".join(illustration)
        else:
            article_tail = ""

        # 全文
        article = article_head + "\n\n\n\n" + article_content + "\n\n\n" + article_tail + \
                  ("\n\n\n-----评论-----\n\n" + "\n".join(comm_list) if comm_list else "")
        article = article.encode("utf-8", errors="replace").decode("utf-8", errors="replace")

        # 文件名
        if blog_info["blog_type"] == "article":
            # 文章用 文章名by作者，替换掉非法字符
            file_name = "{} by {}.txt".format(title, author_name)
            file_name = file_name.replace("/", "&").replace("|", "&").replace("\\", "&").replace("<", "《") \
                .replace(">", "》").replace(":", "：").replace('"', '”').replace("?", "？").replace("*", "·"). \
                replace("\n", "").replace("(", "（").replace(
                ")", "）").replace(",", "，").replace("\t", " ")
            file_name = re.compile('[\\x00-\\x08\\x0b-\\x0c\\x0e-\\x1f]').sub(' ', file_name)
            file_name = l13_like_share_tag.filename_check(file_name, article, arthicle_path, "txt")
        else:
            # 文本要检查是否重名
            file_name = l13_like_share_tag.filename_check(title + ".txt", article, arthicle_path, "txt")

        # 写入
        with open(arthicle_path + "/" + file_name, "w", encoding="utf-8") as op:
            op.write(article)
        try:
            print("{}  保存完毕".format(file_name))
        except:
            print("{}  保存完毕".format(print_title))
        all_file_name.append(file_name)
    return all_file_name


def run(author_url, get_comm, additional_break, start_time, end_time, merge_titles, additional_chapter_index):
    author_page_parse = etree.HTML(
        requests.get(author_url+"/view", headers=useragentutil.get_headers()).content.decode("utf-8"))
    # id是是获取归档页面需要的一个参数，纯数字；ip是作者在lofter的三级域名，由作者注册时设定
    author_id = author_page_parse.xpath("//body//iframe[@id='control_frame']/@src")[0].split("blogId=")[1]
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
    all_file_name = save_file(blog_infos, author_name, author_ip, get_comm, additional_break)
    all_file_name.reverse()
    print("保存完毕")
    if merge_titles:
        merge_chapter(merge_titles, arthicle_path, additional_chapter_index, all_file_name)


def merge_chapter(merge_titles, file_path, additional_chapter_index, all_file_names):
    """
    章节合并版本3
    :param merge_titles: 要合并的标题
    :param file_path: 文件路径
    :param additional_chapter_index: 额外章节序号
    :param all_file_names: 作者归档页的所有文件名，按时间顺序的
    :return:
    """
    print("开始章节合并")
    merge_path = file_path + "/merge_file"
    origin_path = file_path + "/origin_file"
    for x in [merge_path, origin_path]:
        if not os.path.exists(x):
            os.makedirs(x)
    author_name = all_file_names[0].split("by ")[1].split(".txt")[0]

    all_move_filename = set()
    for merge_title in merge_titles:
        chapter_names = []
        for filename in all_file_names:
            if merge_title in filename:
                chapter_names.append(filename)
                all_move_filename.add(filename)

        result = ""
        chapter_index = 1
        for chapter in chapter_names:
            with open(file_path + "/" + chapter, "r", encoding="utf-8") as op:
                file1 = op.read()
            if additional_chapter_index:
                result += "第{}章\n".format(chapter_index)
                chapter_index += 1
            result = result + file1 + "\n\n"
        with open(merge_path + "/" + merge_title + " by " + author_name + ".txt", "w", encoding="utf-8") as op:
            op.write(result)

        print("{} 共 {} 章，合并完成".format(merge_title, len(chapter_names)))
        try:
            chapter_names = [x.split("by")[0] for x in chapter_names]
            print("包括文件{}".format(chapter_names))
        except:
            print("包括文件： [文件名中含特殊字符，无法输出]")
        print("")

    for filename in all_move_filename:
        shutil.move(file_path + "/" + filename, origin_path + "/" + filename)
    print("章节合并结束，合并后的文件位于{}，源文件已移动到{}".format(merge_path, origin_path))


def merge_chapter_al(merge_titles, file_path, additional_chapter_index):
    """
    章节合并版本2，比版本3麻烦点，日期重复的需要手动排序，但是它可以不经过下载单独调用（不需要all_file_names），所以留着，说不定以后会有用
    :param merge_titles: 要合并的标题
    :param file_path: 文件路径
    :param additional_chapter_index: 额外章节序号
    :return:
    """
    print("开始章节合并")
    merge_path = file_path + "/merge_file"
    origin_path = file_path + "/origin_file"
    for x in [merge_path, origin_path]:
        if not os.path.exists(x):
            os.makedirs(x)
    files = os.listdir(file_path)
    author_name = files[0].split("by ")[1].split(".txt")[0]

    title_dict = {}
    # 先找出来带目标标题的
    for merge_title in merge_titles:
        title_dict[merge_title] = []
        for file_name in files:
            if merge_title in file_name:
                title_dict[merge_title].append(file_name)
    # 获取发表时间
    for title, filenames in title_dict.items():
        public_timestamps = []
        for filename in filenames:
            with open(file_path + "/" + filename, "r", encoding="utf-8") as op:
                op.readline()
                public_time = op.readline().strip().split("：")[1]
            public_timestamp = time.mktime(time.strptime(public_time, "%Y-%m-%d"))
            public_timestamps.append(public_timestamp)

        # 日期重复的手动排序
        time_count = dict(Counter(public_timestamps))
        # 找到重复元素
        duplication_times = [key for key, value in time_count.items() if value > 1]
        if duplication_times:
            np_time = np.array(public_timestamps)
            for duplication_time in duplication_times:
                duplication_indexs = np.where(np_time == duplication_time)[0]
                tmp_titles = [filenames[index] for index in duplication_indexs]

                # 手动输入顺序
                while True:
                    str1 = input(
                        "以下章节日期重复，需手动排序：\n{}\n请按你认为正确的顺序输入文件名，文件名间用英文逗号分割，完成后回车，注意不要输入多余空格\n".format(
                            "\n".join(tmp_titles)))
                    sort_titles = str1.split(",")
                    if len(sort_titles) == len(tmp_titles):
                        try:
                            [filenames.index(title) for title in sort_titles]
                        except:
                            print("输入有误，请重新输入")
                            continue
                        break
                    else:
                        print("输入有误，请重新输入")
                a = 0
                for sort_title in sort_titles:
                    public_timestamps[filenames.index(sort_title)] += a
                    a += 1

        publictime_and_title = dict(zip(public_timestamps, filenames))
        sort_publictime_and_title = sorted(publictime_and_title.items(), key=lambda x: x[0])
        print(sort_publictime_and_title)

        result = ""
        chapter_index = 1
        for public_time, filename in sort_publictime_and_title:
            with open(file_path + "/" + filename, "r", encoding="utf-8") as op:
                file1 = op.read()
            if additional_chapter_index:
                result += "第{}章\t".format(chapter_index)
                chapter_index += 1
            result = result + file1 + "\n\n"

            shutil.move(file_path + "/" + filename, origin_path + "/" + filename)

            with open(merge_path + "/" + title + " by " + author_name + ".txt", "w", encoding="utf-8") as op:
                op.write(result)
            print("{} 共 {} 章，合并完成".format(title, len(sort_publictime_and_title)))
            try:
                filenames = [filename.split("by")[0] for filename in dict(sort_publictime_and_title).values()]
                print("包括文件{}".format(filenames))
            except:
                print("包括文件： [文件名中含特殊字符，无法输出]")
            print("")
        print("章节合并结束，合并后的文件位于{}，源文件已移动到{}".format(merge_path, origin_path))


if __name__ == '__main__':
    # 作者的主页地址   示例 https://ishtartang.lofter.com/   *最后的'/'不能少
    author_url = "https://jimohechu.lofter.com/"

    # ### 自定义部分 ### #

    # 是否爬取评论，1为爬取，0为不爬取
    get_comm = 0

    # 额外换行，默认0，设为1的话会在每个解析段之间多加一次换行，2就是多两次换行，视情况和你的阅读习惯设置
    additional_break = 0

    # 设定爬取哪个时间段的博客，空值为不设定 格式："yyyy-MM-dd" 例："2020-05-01"
    start_time = ""
    end_time = ""

    # 章节合并：标题包含指定内容会自动合并，合并后会用你写的标题作为文件名，合并文件里章节的顺序按作者发布顺序，空值为不合并
    chapter_merge_title = []
    # 额外章节序号: 合并后的文件在每章前加入"第n章"，方便一些阅读软件自动分章（只是单纯的按顺序标号，并不能自动判断原标题是第几章）
    # 1启动，0关闭，chapter_merge_title为空时无效
    additional_chapter_index = 0

    run(author_url, get_comm, additional_break, start_time, end_time, chapter_merge_title, additional_chapter_index)
