import json
import os
import re
import shutil
import time
import requests
import html2text
from urllib import parse
from lxml.html import etree
from requests.cookies import RequestsCookieJar

import useragentutil

"""
sessionStartTime		seesion建立的时间，不用动	同一次刷新中不变    页面刷新没变
persistedTime		不晓得？	同一次刷新中不变	页面刷新没变
updatedTime		页面刷新的时间，在同一次刷新中是不变的，不用动	页面刷新会改变	
LASTEVENT["time"]		我以为是当前时间，但是它一直没动，而且跟updatedTime几乎相同，差值1到2，同一次刷新中不变	页面刷新改变
sendNumClass["allNum"]	？每次刷新页面会加一，有的时候不知道为啥会加一，一般不变
NTESwebSI		每次请求都会变，新值由上一次的请求返回，如果上次请求没有返回新值可以继续用旧值
"""


def write_html(html):
    with open("./example.html", "w", encoding="utf-8") as op:
        op.write(html)


# 保存文本
def write_text(file, filename, path):
    filename = filename.replace("\r", "")
    with open(path + "/" + filename, "w", encoding="utf-8", errors="ignore") as op:
        op.write(file)


# 保存图片
def write_img(file, filename, path):
    with open(path + "/" + filename, "wb") as op:
        op.write(file)


def get_logion_session(login_info):
    """
    获取一个登录过的session
    :param login_info:
    :return: session
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/79.0.3945.88 Safari/537.36",
        "Host": "www.lofter.com",
        # "Referer": "https://www.lofter.com/login?urschecked=true"
    }
    session = requests.session()
    payload = {"urschecked": "true"}

    session.headers = headers

    # 请求登录页
    logion_page_url = "http://www.lofter.com/login"
    login_page_response = session.get(logion_page_url, params=payload)
    print("登录页状态码 {}".format(login_page_response.status_code))

    # 改请求头和cookies
    headers["Referer"] = "http://www.lofter.com/login"
    session.headers = headers

    # 主页参数设置
    homepage_url = "http://www.lofter.com/"
    cookies = session.cookies
    cookies.set(login_info["login_key"], login_info["login auth"])
    session.cookies = cookies

    # 请求主页
    response = session.get(homepage_url)
    write_html(response.content.decode("utf-8"))
    print("主页请求状态码 {}".format(response.status_code))

    return session


def make_data(mode, session, url=""):
    """
    :param mode: 模式，支持的模式有share like1 like2 tag
    :param url:  生成data需要用到url，share like1 需要的是用户主页的url，tag需要的是tag页的url。like2不会用到，因为信息在cookies种
    :return: 初始data
    """
    if (mode == "like1" or mode == "share" or mode == "tag") and url == "":
        print("{}模式生成data需要url参数".format(mode))
        return {}

    base_data = {'callCount': '1',
                 'httpSessionId': '',
                 'scriptSessionId': '${scriptSessionId}187',
                 'c0-id': '0',
                 "batchId": "472351"}
    get_num = 100
    got_num = 0
    if mode == "share" or mode == "like1":
        userId = ""
        host = re.search("https://(.*?)/", url).group(1)
        headers = session.headers
        headers["Host"] = host
        x = session.get(url, headers=headers).content.decode("utf-8")
        user_page_parse = etree.HTML(x)
        try:
            userId = user_page_parse.xpath("//body/iframe[@id='control_frame']/@src")[0].split("blogId=")[1]
        except:
            print("\n用户主页登录验证失败")
            exit()
        data_parme = {
            'c0-scriptName': 'BlogBean',
            "c0-methodName": "",
            'c0-param0': 'number:' + str(userId),
            'c0-param1': 'number:' + str(get_num),
            'c0-param2': 'number:' + str(got_num),
            'c0-param3': 'string:'}
        if mode == "like1":
            data_parme["c0-methodName"] = "queryLikePosts"
        else:
            data_parme["c0-methodName"] = "querySharePosts"

    elif mode == "like2":
        data_parme = {"c0-scriptName": "PostBean",
                      "c0-methodName": "getFavTrackItem",
                      "c0-param0": "number:" + str(get_num),
                      "c0-param1": "number:" + str(got_num),
                      }
    elif mode == "tag":
        # 参数8要拿时间戳
        url_search = re.search("http[s]{0,1}://www.lofter.com/tag/(.*?)/(.*)", url)
        type = url_search.group(2)
        if type == "":
            type = "new"
        data_parme = {'c0-scriptName': 'TagBean',
                      'c0-methodName': 'search',
                      'c0-param0': 'string:' + url_search.group(1),
                      'c0-param1': 'number:0',
                      'c0-param2': 'string:',
                      'c0-param3': 'string:' + type,
                      'c0-param4': 'boolean:false',
                      'c0-param5': 'number:0',
                      'c0-param6': 'number:' + str(get_num),
                      'c0-param7': 'number:' + str(got_num),
                      'c0-param8': 'number:' + str(int(time.time() * 1000)),
                      'batchId': '870178'}
    else:
        print("data-模式错误")
        data_parme = {}
    data = {**base_data, **data_parme}
    return data


def make_header(mode, url=""):
    if (mode == "like1" or mode == "share" or mode == "tag") and url == "":
        print("{}模式生成headers需要url参数".format(mode))
        return {}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/79.0.3945.88 Safari/537.36",
        "Host": "www.lofter.com",
    }
    if mode == "share" or mode == "like1":
        userName = re.search("http[s]{0,1}://(.*?).lofter.com/", url).group(1)
        if mode == "share":
            headers["Referer"] = "https://www.lofter.com/shareblog/" + userName
        elif mode == "like1":
            headers["Referer"] = "https://www.lofter.com/favblog/" + userName
    elif mode == "like2":
        headers["Referer"] = "http://www.lofter.com/like"
    elif mode == "tag":
        headers["Referer"] = url

    return headers


def update_data(mode, data, get_num, got_num, last_timestamp="0"):
    """
    获取归档页时，每个请求都需要根据上次获取的内容更新data，才能成功获取到下一页的内容
    :param mode:    模式
    :param data:    原data
    :param get_num: 要获取的条数
    :param got_num: 已获取的条数
    :param last_timestamp:  tag模式需要上次获取的最后一条博客的发表时间戳作为参数
    :return:    更新后的data
    """
    if (mode == "like1" or mode == "share" or mode == "tag") and last_timestamp == "":
        print("tag模式更新data需要last_timestamp参数")
        return data

    if mode == "share" or mode == "like1":
        data["c0-param1"] = 'number:' + str(get_num)
        data["c0-param2"] = 'number:' + str(got_num)
    elif mode == "like2":
        data["c0-param0"] = 'number:' + str(get_num)
        data["c0-param1"] = 'number:' + str(got_num)
    elif mode == "tag":
        data["c0-param6"] = 'number:' + str(get_num)
        data["c0-param7"] = 'number:' + str(got_num)
        data["c0-param8"] = 'number:' + str(last_timestamp)
    else:
        print("模式{}无匹配项".format(mode))
    return data


def save_all_fav(url, mode, file_path, login_info, start_time):
    # 获取所有博客信息，按条数切分

    # 各种设置，不同模式使用不用链接
    real_got_num = 0
    got_num = 0
    get_num = 100
    rlike1_url = "https://www.lofter.com/dwr/call/plaincall/BlogBean.queryLikePosts.dwr"
    rlike2_url = "http://www.lofter.com/dwr/call/plaincall/PostBean.getFavTrackItem.dwr"
    rshare_url = "https://www.lofter.com/dwr/call/plaincall/BlogBean.querySharePosts.dwr"
    rtag_url = "http://www.lofter.com/dwr/call/plaincall/TagBean.search.dwr"
    requests_url = ""
    if mode == "share":
        requests_url = rshare_url
    elif mode == "like1":
        requests_url = rlike1_url
    elif mode == "like2":
        requests_url = rlike2_url
    elif mode == "tag":
        requests_url = rtag_url
    else:
        print("requests_url 模式匹配错误 当前模式{}".format(mode))
        exit()
    # like2需要登录的session,其他模式不用
    # if mode == "like2":
    #     session = get_logion_session(login_info)
    # else:
    #     session = requests.session()
    #     session.headers = make_header(mode, url)

    session = get_logion_session(login_info)
    data = make_data(mode, session, url)

    fav_info = []
    if start_time:
        start_time_stamp = time.mktime(time.strptime(start_time, "%Y-%m-%d"))
    else:
        start_time_stamp = 0

    # 开始获取归档页
    while True:
        print("正在获取{}-{}".format(got_num, got_num + get_num), end="\t")
        fav_response = session.post(requests_url, data=data)
        content = fav_response.content.decode("utf-8")
        # activityTags应该是第一或者第二个属性，从这切差不多能保证信息完整
        new_info = content.split("activityTags")[1:]
        fav_info += new_info
        got_num += get_num
        real_got_num += len(new_info)
        print("实际返回条数 {}".format(len(new_info)), end="\t")

        str1 = ""
        if mode == "like1" or mode == "like2":
            str1 = "我的喜欢页面"
        elif mode == "share":
            str1 = "我的推荐页面"
        elif mode == "tag":
            str1 = "tag页面"
        """
        调试中
        """

        # 长度为0说明已经到最后一页，或者被lofter发现了
        if len(new_info) == 0:
            print("\n已获取到最后一页，{}信息获取完成".format(str1))
            break

        last_timestamp = 0
        last_optime = "/"
        last_hot = 0
        # mode2会输出最后一条的点赞时间
        if mode == "like2":
            try:
                last_timestamp = int(re.search('s\d{1,5}.opTime=(.*?);', new_info[-1]).group(1)) / 1000
                last_optime = time.strftime("%Y-%m-%d", time.localtime(last_timestamp))
            except:
                pass
            print("最后一条的时间为 {}".format(last_optime), end="")
            # like2独有的最早时间指定。optime是点赞时间
            if start_time and last_timestamp < start_time_stamp:
                print()
                print(start_time_stamp)
                print(last_timestamp)
                print("\n已获取到指定时间内所有博客，信息获取完成")
                break
        elif mode == "tag":
            try:
                last_hot = int(re.search('s\d{1,5}.hot=(.*?);', new_info[-1]).group(1))
            except:
                pass
            print("最后一条热度为 {}".format(last_hot), end="")

        # 更新data
        if mode == "tag":
            last_info = new_info[-1]
            last_public_timestamp = re.search('s\d{1,5}.publishTime=(.*?);', last_info).group(1)
            data = update_data(mode, data, get_num, got_num, last_public_timestamp)
        else:
            data = update_data(mode, data, get_num, got_num)
        print()

    # 归档页出来了啥都没获取到
    if len(fav_info) == 0:
        print("归档页获取异常，请检查网络是否正常，模式与链接是否匹配，like2请检查登录信息是否有误")
        exit()

    file = open(file_path + "/blogs_info", "w", encoding="utf-8")
    for info in fav_info:
        file.write(info.replace("\n", ""))
        file.write("\n\nsplit_line\n\n")
    print("总请求条数：{}  实际返回条数：{}".format(got_num, real_got_num))


def infor_formater(favs_info, fav_str, mode, file_path, start_time, min_hot, print_level):
    # 把字段从原文件中提取出来，大部分使用正则

    format_fav_info = []
    start_time_stamp = ""
    if start_time:
        start_time_stamp = time.mktime(time.strptime(start_time, "%Y-%m-%d"))

    for fav_info in favs_info:
        blog_info = {}
        # 博客链接
        try:
            url = re.search('s\d{1,5}.blogPageUrl="(.*?)"', fav_info).group(1)
        except:
            print("博客{} 信息丢失，跳过".format(favs_info.index(fav_info) + 1))
            continue
        blog_info["url"] = url
        if print_level:
            print("博客{} {}准备解析".format(favs_info.index(fav_info) + 1, url), end="\t")

        # 喜欢时间
        fav_timestamp = re.search('s\d{1,5}.opTime=(.*?);', fav_info).group(1)
        # 模式为like2且早于设定时间则跳出整理
        if mode == "like2" and start_time:
            if int(fav_timestamp) / 1000 < start_time_stamp:
                print("已将指定时间内的博客解析结束")
                break
        blog_hot = int(re.search('s\d{1,5}.hot=(.*?);', fav_info).group(1))
        if mode == "tag" and blog_hot < min_hot:
            print("当前博客的热度小于设定热度，跳过")
            continue
        time_local2 = time.localtime(int(int(fav_timestamp) / 1000))
        fav_time = time.strftime("%Y-%m-%d", time_local2)
        blog_info["fav time"] = fav_time

        # 作者名
        author_name_search = re.search('s\d{1,5}.blogNickName="(.*?)"', fav_info)

        if author_name_search:
            author_name = author_name_search.group(1).encode('latin-1').decode('unicode_escape', errors="replace")
        # 正则没有匹配出来的话说明这一页的前面也有这个作者的博客，作者信息在前面，找到id再在前面搜索作者信息
        else:
            info_id = re.search("s\d{1,5}.blogInfo=(s\d{1,5})", fav_info).group(1)
            test_names = re.findall(info_id + '.blogNickName="(.*?)"', fav_str.split('blogPageUrl="' + url + '"')[0])
            author_name = test_names[-1].encode('latin-1').decode('unicode_escape', errors="replace")
        blog_info["author name"] = author_name

        # 文件中不允许出现的字符，在用于文件名时要全部替换掉，英文括号换成中文括号，避免在检查文件名重复时被切割
        author_name_in_filename = author_name.replace("/", "&").replace("|", "&").replace("\r", " ").replace(
            "\\", "&").replace("<", "《").replace(">", "》").replace(":", "：").replace('"', '”').replace("?", "？") \
            .replace("*", "·").replace("\n", "").replace("*", "·").replace("\n", "").replace("(", "（").replace(")",
                                                                                                               "）").replace(
            "\t", " ").strip()
        author_name_in_filename = re.compile('[\\x00-\\x08\\x0b-\\x0c\\x0e-\\x1f]').sub(' ', author_name_in_filename)
        blog_info["author name in filename"] = author_name_in_filename
        # 作者ip
        author_ip = re.search("http[s]{0,1}://(.*?).lofter.com", url).group(1)
        blog_info["author ip"] = author_ip
        # 发表时间
        public_timestamp = re.search('s\d{1,5}.publishTime=(.*?);', fav_info).group(1)
        time_local1 = time.localtime(int(int(public_timestamp) / 1000))
        public_time = time.strftime("%Y-%m-%d", time_local1)
        blog_info["public time"] = public_time
        # tags
        tags = re.search('s\d{1,5}.tag[s]{0,1}="(.*?)";', fav_info).group(1).strip().encode('utf-8').decode(
            'unicode_escape').split(",")
        if tags[0] == "":
            tags = []
        lower_tags = []
        for tag in tags:
            # 转小写，全角空格转半角
            lower_tag = tag.lower().replace(" ", " ").strip()
            lower_tags.append(lower_tag)
        blog_info["tags"] = lower_tags
        # 标题
        try:
            title = re.search('s\d{1,5}.title="(.*?)"', fav_info).group(1).encode('latin-1').decode('unicode_escape',
                                                                                                    errors="ignore ")
        except:
            title = ""
        title_in_filename = title.replace("/", "&").replace("|", "&").replace("\r", " ").replace(
            "\\", "&").replace("\t", " ") \
            .replace("<", "《").replace(">", "》").replace(":", "：").replace('"', '”').replace("?", "？") \
            .replace("*", "·").replace("\n", "").replace("(", "（").replace(")", "）").strip()
        title_in_filename = re.compile('[\\x00-\\x08\\x0b-\\x0c\\x0e-\\x1f]').sub(' ', title_in_filename)
        blog_info["title"] = title
        blog_info["title in filename"] = title_in_filename

        # 图片链接
        img_urls = []
        urls_search = re.search('originPhotoLinks="(\[.*?\])"', fav_info)
        if urls_search:
            urls_str = urls_search.group(1).replace("\\", "").replace("false", "False").replace("true", "True")
            urls_infos = eval(urls_str)
            for url_info in urls_infos:
                # raw是没有任何后缀的原图，但有的没有raw，取orign
                try:
                    url = url_info["raw"]
                except:
                    url = url_info["orign"].split("?imageView")[0]
                if "netease" in url:
                    url = url_info["orign"].split("?imageView")[0]
                img_urls.append(url)
        blog_info["img urls"] = img_urls

        # 正文内容
        tmp_content1 = re.search('s\d{1,5}.content="(.*?)";', fav_info).group(1)
        parse = etree.HTML(tmp_content1)
        # if tmp_content1:
        #     f = parse.xpath("//p//text()")
        #     tmp_content2 = "\n".join(f)
        #     content = tmp_content2.encode('latin-1').decode("unicode_escape", errors="ignore").strip()
        # else:
        #     content = ""
        # blog_info["content"] = content
        content = html2text.html2text(tmp_content1.encode('latin-1').decode("unicode_escape", errors="ignore"))
        blog_info["content"] = content

        # 文章中插的图片
        illustration = []
        if tmp_content1:
            # 匹配新格式
            img_src = parse.xpath("//img/@src")
            illustration = re.findall('"(http[s]{0,1}://imglf\d{0,1}.lf\d*.[0-9]{0,3}.net.*?)\?', "\n".join(img_src))
            if illustration == []:
                # 匹配旧格式
                illustration = re.findall('"(http[s]{0,1}://imglf\d{0,1}.nosdn\d*.[0-9]{0,3}.net.*?)\?',
                                          "\n".join(img_src))

        blog_info["illustration"] = illustration

        # 外链
        if tmp_content1:
            link_a = parse.xpath("//a/@href")
            external_link = list(map(lambda x: x.replace("\\", "").replace('"', ''), link_a))
        else:
            external_link = []
        blog_info["external link"] = external_link

        # 长文章
        l_content = ""
        l_cover = ""
        l_url = []
        l_img = []
        long_article = re.search('s\d{1,5}.compositeContent="(.*?)";s\d{1,5}', fav_info)
        try:
            if long_article:
                long_article1 = long_article.group(1)
                parse = etree.HTML(long_article.group(1))
                l_cover = re.search('s\d{1,5}.banner="(.*?)";', fav_info).group(1)
                l_url = parse.xpath("//a//@href")
                l_url = list(map(lambda x: x.replace("\\", "").replace('"', ''), l_url))
                l_img = parse.xpath("//img/@src")
                l_img = list(map(lambda x: x.replace("\\", "").replace('"', ''), l_img))
                l_content = c = re.sub('<[^<]+?>', '', long_article1).replace("&nbsp;", " ").strip()
                l_content = l_content.encode('latin-1').decode("unicode_escape", errors="ignore").strip()
        except:
            # print("长文章 {} 被屏蔽，无法获取正文".format(url))
            pass
        blog_info["long article content"] = l_content
        blog_info["long article url"] = l_url
        blog_info["long article img"] = l_img
        blog_info["long article cover"] = l_cover

        # video_url_search = re.findall('"originUrl":""')

        # 整合后输出
        format_fav_info.append(blog_info)
        if print_level:
            print("解析完成，具体信息：\n{}".format(blog_info))
            print("----" * 20)
        else:
            if favs_info.index(fav_info) % 100 == 0 or len(format_fav_info) == len(favs_info):
                print("解析进度 {}/{}   正在解析的博客链接 {}".format(len(format_fav_info), len(favs_info), blog_info["url"]))
    # 写入到文件
    with open(file_path + "/format_blogs_info.json", "w", encoding="utf-8", errors="ignore") as op:
        op.write(json.dumps(format_fav_info, ensure_ascii=False, indent=4))


# 向博客信息中加入key tag
def update_key_tag(blogs_info, classify_by_tag, prior_tags, agg_non_prior_tag):
    # 初始化所有key tag
    for blog_info in blogs_info:
        blog_info["key tag"] = ""
    # 没有启动按tag整理，直接返回
    if not classify_by_tag:
        return blogs_info
    # 启动按tag整理
    for blog_info in blogs_info:
        if blog_info["tags"]:

            for prior_tag in prior_tags:
                # 优先tag中有内容时表示启用优先tag，尝试在tag列表中找优先tag，如果找到，跳出tag循环，继续匹配下一条博客
                if prior_tag.lower() in blog_info["tags"]:
                    blog_info["key tag"] = prior_tag
                    break
            # 如果key tag仍为空说明未启用优先tag，或其中没有优先tag
            if blog_info["key tag"] == "":
                # 启用优先tag且启用非优先tag聚合时 key tag为other
                if agg_non_prior_tag and prior_tags:
                    blog_info["key tag"] = "other"
                else:
                    # 未启用优先tag或者启用优先tag未启用非优先tag聚合，key tag为作者的第一个tag
                    blog_info["key tag"] = blog_info["tags"][0]
        else:
            blog_info["key tag"] = "no tag"

    return blogs_info


def classify(blogs_info):
    classified_info = {"img": [], "article": [], "long article": [], "text": []}
    # 分类，有图片链接为图片类型，有长文内容为长文(长文也有标题，必须在文章前面)，有标题为文章，剩余的为文本
    for blog_info in blogs_info:
        if blog_info["img urls"]:
            classified_info["img"].append(blog_info)
        elif blog_info["long article content"]:
            classified_info["long article"].append(blog_info)
        elif blog_info["title"]:
            classified_info["article"].append(blog_info)
        else:
            classified_info["text"].append(blog_info)
    return classified_info


# 每种类型博客统计
def count_type(classified_infos):
    count_dic = {}
    for type in classified_infos:
        count_dic[type] = len(classified_infos[type])
    return count_dic


# tag统计
def count_tag(blogs_info):
    # 先找出所有tag
    tag_count1 = []
    for blog in blogs_info:
        for tag in blog["tags"]:
            if tag not in tag_count1:
                tag_count1.append(tag)

    # 用拿到的tag构建字典{xxx:0}，进行统计
    tag_count2 = {}
    for tag in tag_count1:
        tag_count2[tag] = 0
    for blog in blogs_info:
        for tag in blog["tags"]:
            tag_count2[tag] += 1
    # 排序，排序完成后会变成tuple，再转成字典
    tag_count3 = {}
    dict = sorted(tag_count2.items(), key=lambda d: d[1], reverse=True)
    for tuple1 in dict:
        tag_count3[tuple1[0]] = tuple1[1]
    return tag_count3


# 获取文本尾
def get_tail(blog_info):
    article_tail = ""

    if blog_info["external link"]:
        article_tail += "文章中包含的外部连接"
        for external_links in blog_info["external link"]:
            article_tail += "\n" + external_links
    if blog_info["illustration"]:
        article_tail += "\n\n文章中包含的图片连接："
        for illustration in blog_info["illustration"]:
            article_tail += "\n" + illustration
    return article_tail


# 文件名检查，避免重名
def filename_check(filename, file, path, file_type):
    if os.path.exists(path + "/" + filename):
        # 如果文件已存在,读取文件内容
        if file_type == "txt":
            exist_file = open(path + "/" + filename, "r", encoding="utf-8").read()
        else:
            exist_file = open(path + "/" + filename, "rb").read()
        # 如果文件内容跟要保存的内容相同,返回文件名
        if exist_file == file:
            return filename
        # 如果文件内容跟要保存的内容不同,在文件名加后缀 (num)
        num = 2
        while True:
            filename = filename.split("." + file_type)[0].split("(")[0] + "(" + str(num) + ")." + file_type
            # 检测新文件名是否也有已存在文件,存在则增加后缀中的数字,不存在则跳出循环,返回文件名
            if os.path.exists(path + "/" + filename):
                if file_type == "txt":
                    exist_file = open(path + "/" + filename, "r", encoding="utf-8").read()
                else:
                    exist_file = open(path + "/" + filename, "rb").read()
                if exist_file == file:
                    return filename
                num += 1
            else:
                break
    return filename


# 保存文章（带标题）
def save_article(articles_info, file_path, classify_by_tag, prior_tags, agg_non_prior_tag, save_img_in_text,
                 print_level):
    # 在启用按tag分类时，先建立优先prior和other文件夹
    if classify_by_tag and prior_tags:
        for x in ["prior", "other"]:
            if not os.path.exists(file_path + "/article/" + x):
                os.makedirs(file_path + "/article/" + x)
    count = 0
    is_tag_null = lambda x: x if x != "" else "无"

    for article_info in articles_info:
        # 文档信息整理
        article_head = article_info["title"] + " by " + article_info["author name"] + "[" + article_info[
            "author ip"] + "]" + "\n发表时间：" + article_info["public time"] + "\n原文连接：" + article_info["url"] \
                       + "\ntags：" + is_tag_null(", ".join(article_info["tags"]))

        article_tail = get_tail(article_info)
        article = article_head + "\n\n\n" + article_info["content"] + "\n\n\n" + article_tail
        filename_title = article_info["title in filename"]
        filename = filename_title + " by " + article_info["author name in filename"] + ".txt"
        count += 1
        # 提示输出
        if print_level:
            try:
                print(
                    "保存：文章序号{} {} 原文链接：{}".format(articles_info.index(article_info) + 1, filename, article_info["url"]),
                    end="\t\t")
            except:
                print(
                    print("保存：文章序号{} 原文链接：{}".format(articles_info.index(article_info) + 1, article_info["url"]),
                          end="\t\t"))
        else:
            if count % 20 == 0 or count == len(articles_info) or count == 0:
                try:
                    print("保存进度 {}/{}\t\t{}".format(count, len(articles_info), filename), end="\t\t")
                except:
                    print("保存进度 {}/{}\t\t".format(count, len(articles_info)), end="\t\t")

        # 文件路径判断
        # 没有启动tag分类
        key_tag_path = article_info["key tag"].replace("/", "&").replace("|", "&").replace("\\", "&") \
            .replace("<", "《").replace(">", "》").replace(":", "：").replace('"', '”').replace("?", "？") \
            .replace("*", "·").replace("(", "（").replace(")", "）")
        if not classify_by_tag:
            article_path = file_path + "/article"
        # 启动tag分类，未启用优先tag
        elif classify_by_tag and not prior_tags:
            article_path = file_path + "/article/" + key_tag_path
        # 启用tag分类，启用优先tag
        else:
            # key tag在优先tag中
            if article_info["key tag"] in prior_tags:
                article_path = file_path + "/article/prior/" + key_tag_path
            # tag不在优先tag
            else:
                # tag不在优先tag中，启用非优先tag聚合
                if agg_non_prior_tag:
                    article_path = file_path + "/article/other"
                # tag不在优先tag中，未启用非优先tag聚合
                else:
                    article_path = file_path + "/article/other/" + key_tag_path

        # 如果文件夹不存在，建立文件夹
        if not os.path.exists(article_path):
            os.makedirs(article_path)
        # 保存
        write_text(article, filename, article_path)
        # 保存文章中的图片
        if save_img_in_text:
            if article_info["illustration"]:
                for img_url in article_info["illustration"]:
                    if print_level:
                        print("准备保存文章中的图片 {}".format(img_url), end="\t\t")
                    img_name = filename_title + " by " + article_info["author name in filename"] + ".jpg"
                    img = requests.get(img_url, headers=useragentutil.get_headers()).content
                    img_name = filename_check(img_name, img, article_path, "jpg")
                    write_img(img, img_name, article_path)
                    if print_level:
                        print("保存完成")

        # 输出
        if print_level:
            print("保存完成")
        else:
            if count % 20 == 0 or count == len(articles_info):
                print("保存完成")


# 保存文本（不带标题）
def save_text(texts_info, file_path, save_img_in_text):
    if not os.path.exists(file_path + "/text"):
        os.makedirs(file_path + "/text")
    count = 0
    is_tag_null = lambda x: x if x != "" else "无"
    for text_info in texts_info:
        count += 1
        # 文档整理
        text_head = text_info["author name"] + "[" + text_info["author ip"] + "]\n发表时间：" + text_info["public time"] \
                    + "\n原文连接：" + text_info["url"] + "\ntags：" + is_tag_null(", ".join(text_info["tags"]))
        text_tial = get_tail(text_info)
        text = text_head + "\n\n\n" + text_info["content"] + "\n\n\n" + text_tial

        first_tag = "无tag"
        if text_info["tags"]:
            first_tag = text_info["tags"][0]
        filename = text_info["author name in filename"] + "-" + first_tag + "-" + text_info["public time"] + ".txt"
        filename = filename_check(filename, text, file_path + "/text", "txt")

        # 提示输出
        if count % 10 == 0 or count == len(texts_info):
            try:
                print("保存进度 {}/{}\t\t{}".format(count, len(texts_info), filename), end="\t\t")
            except:
                print("保存进度 {}/{}\t\t{}".format(count, len(texts_info), "文件名异常"), end="\t\t")

        # 保存
        write_text(text, filename, file_path + "/text")
        # 保存文字中的图片

        if save_img_in_text:
            if text_info["illustration"]:
                for img_url in text_info["illustration"]:
                    img_name = text_info["author name in filename"] + "-" + first_tag + "-" + text_info[
                        "public time"] + ".jpg"

                    # img_name = text_info + " by " + text_info["author name in filename"] + ".jpg"
                    img = requests.get(img_url, headers=useragentutil.get_headers()).content
                    img_name = filename_check(img_name, img, file_path + "/text", "jpg")
                    write_img(img, img_name, file_path + "/text")
        if count % 10 == 0 or count == len(texts_info):
            print("保存完成")


# 保存长文章
def save_long_article(long_articles_info, file_path, save_img_in_text):
    if not os.path.exists(file_path + "/long article"):
        os.makedirs(file_path + "/long article")
    count = 0
    is_tag_null = lambda x: x if x != "" else "无"
    for l_info in long_articles_info:
        # 文档整理
        l_head = l_info["title"] + " by " + l_info["author name"] + "[" + l_info["author ip"] + "]" + "\n发表时间：" \
                 + l_info["public time"] + "\n原文连接：" + l_info["url"] + "\ntags：" + \
                 is_tag_null(", ".join(l_info["tags"]))
        l_tail = ""
        if l_info["long article url"]:
            l_tail += "文章中包含的外部连接"
            for external_links in l_info["long article url"]:
                l_tail += "\n" + external_links
        if l_info["long article img"]:
            l_tail += "\n\n文章中包含的图片连接："
            for illustration in l_info["long article img"]:
                l_tail += "\n" + illustration
        long_article = l_head + "\n\n\n" + l_info["long article content"] + "\n\n\n" + l_tail
        filename = l_info["title in filename"] + " by " + l_info["author name in filename"] + ".txt"

        count += 1
        # 输出
        if count % 5 == 0 or count == len(long_articles_info) or count == 1:
            print("保存进度 {}/{}\t\t{}".format(count, len(long_articles_info), filename), end="\t\t")
        # 保存
        write_text(long_article, filename, file_path + "/long article")
        # 保存文本中的图片
        if save_img_in_text:
            if l_info["long article img"]:
                for img_url in l_info["long article img"]:
                    # re_url = re.findall('http[s]{0,1}://imglf\d{0,1}.nosdn\d*.[0-9]{0,3}.net.*', img_url)
                    re_url = re.findall('http[s]{0,1}://imglf\d{0,1}.lf\d*.[0-9]{0,3}.net.*', img_url)
                    if not re_url:
                        print("\n图片 {} 不是lofter站内图 可能会保存失败".format(img_url), end="\t")
                    try:
                        img = requests.get(img_url, headers=useragentutil.get_headers()).content
                    except:
                        print("保存失败，请尝试手动保存", end="\t")
                        continue

                    img_name = l_info["title in filename" \
                                      ""] + " by " + l_info["author name in filename"] + ".jpg"
                    img_name = filename_check(img_name, img, file_path + "/long article", "jpg")
                    write_img(img, img_name, file_path + "/long article")

        if count % 5 == 0 or count == len(long_articles_info) or count == 1:
            print("保存完成")


def save_img(imgs_info, file_path, img_save_info, classify_by_tag, prior_tags, agg_non_prior_tag, print_level):
    if not os.path.exists(file_path + "/img"):
        os.makedirs(file_path + "/img")

    if classify_by_tag and prior_tags:
        for x in ["prior", "other"]:
            if not os.path.exists(file_path + "/img/" + x):
                os.makedirs(file_path + "/img/" + x)

    # saved_index是已经保存完成的数量
    count = 0
    saved_num = img_save_info["已保存"]
    for img_info in imgs_info:
        # 跳到上次的保存进度
        if count < saved_num:
            count += 1
            continue
        print_end = lambda x: "\n" if x == 1 else "   "
        print("正在保存：博客序号{} {}".format(count + 1, img_info["url"]), end=print_end(print_level))
        for img_url in img_info["img urls"]:
            is_gif = re.findall("gif", img_url)
            is_png = re.findall("png", img_url)
            if is_gif:
                img_type = "gif"
            elif is_png:
                img_type = "png"
            else:
                img_type = "jpg"

            if print_level:
                print("正在保存图片 {} ".format(img_url), end="\t\t")
            # 检查图片是否是站内图
            # re_url = re.findall('http[s]{0,1}://imglf\d{0,1}.nosdn\d*.[0-9]{0,3}.net.*', img_url)
            re_url = re.findall('http[s]{0,1}://imglf\d{0,1}.lf\d*.[0-9]{0,3}.net.*', img_url)

            if not re_url:
                print("\n图片 {} 不是lofter站内图 ".format(img_url), end="\t")
            try:
                img = requests.get(img_url, headers=useragentutil.get_headers()).content

            except:
                print("保存失败，请尝试手动保存")
                continue
            filename = img_info["author name in filename"] + "[" + img_info["author ip"] + "] " + img_info[
                "public time"] + "." + img_type

            # 根据自动整理选项选择保存路径
            key_tag_path = img_info["key tag"].replace("/", "&").replace("|", "&").replace("\\", "&") \
                .replace("<", "《").replace(">", "》").replace(":", "：").replace('"', '”').replace("?", "？") \
                .replace("*", "·").replace("(", "（").replace(")", "）")
            # 没有启动tag分类
            if not classify_by_tag:
                img_path = file_path + "/img"
            # 启动tag分类，未启用优先tag
            elif classify_by_tag and not prior_tags:
                if not os.path.exists(file_path + "/img/" + key_tag_path):
                    os.makedirs(file_path + "/img/" + key_tag_path)
                img_path = file_path + "/img/" + key_tag_path
            # 启用tag分类，启用优先tag
            else:
                # key tag在优先tag中
                if img_info["key tag"] in prior_tags:
                    img_path = file_path + "/img/prior/" + key_tag_path
                # tag不在优先tag
                else:
                    # tag不在优先tag中，启用非优先tag聚合
                    if agg_non_prior_tag:
                        img_path = file_path + "/img/other"
                    # tag不在优先tag中，未启用非优先tag聚合
                    else:
                        img_path = file_path + "/img/other/" + key_tag_path
            # 文件名查重，保存
            filename = filename_check(filename, img, img_path, img_type)
            if not os.path.exists(img_path):
                os.makedirs(img_path)
            write_img(img, filename, img_path)
            if print_level:
                print("保存完成")
        if not print_level:
            print("保存完成")
        else:
            print("\n" + "-----------" * 10)
        # 保存数+1，每7条博客刷新一次文件
        saved_num += 1
        count += 1
        if saved_num % 7 == 0 or saved_num == len(imgs_info):
            img_save_info["已保存"] = saved_num
            with open(file_path + "/img_save_info.json", "w", encoding="utf-8") as i_op1:
                i_op1.write(json.dumps(img_save_info, indent=4, ensure_ascii=False))


def run(url, mode, save_mode, classify_by_tag, prior_tags, agg_non_prior_tag, login_info, start_time, tag_filt_num,
        min_hot, print_level, save_img_in_text, base_path):
    file_path = base_path
    like1_file_path = base_path + "/like1_file"
    like2_file_path = base_path + "/like2_file"
    share_file_path = base_path + "/share_file"
    tag_file_path = base_path + "/tag_file"
    # 文件保存位置
    if mode == "like1":
        file_path = like1_file_path
    elif mode == "like2":
        file_path = like2_file_path
    elif mode == "share":
        file_path = share_file_path
    elif mode == "tag":
        if url.split("/")[-1] not in ["new", "total", "month", "week", "date"]:
            url += "/new"
        print(url)
        tag = re.search("http[s]{0,1}://www.lofter.com/tag/(.*?)/.*", url).group(1)
        tag = parse.unquote(tag)
        file_path = tag_file_path + "/" + tag
    else:
        print("模式只能为 share、like1、like2或tag")
        exit()

    if not os.path.exists(file_path):
        os.makedirs(file_path)

    # 进度检查

    # 阶段4文件存在但阶段1或阶段2结束文件不存在，删除阶段4文件
    if not os.path.exists(file_path + "/classified_blogs_info.json") or not os.path.exists(
            file_path + "/format_blogs_info.json"):
        if os.path.exists(file_path + "/img_save_info.json"):
            print("找到阶段4进度文件，但阶段1或阶段2文件未找到，阶段4进度被删除")
            os.remove(file_path + "/img_save_info.json")

    # 阶段2结束文件存在但阶段1结束文件不存在，删除阶段2文件
    if os.path.exists(file_path + "/classified_blogs_info.json") and not os.path.exists(
            file_path + "/format_blogs_info.json"):
        print("找到阶段2结束文件，但阶段1结束文件不存在，重置进度到阶段1")
        os.remove(file_path + "/classified_blogs_info.json")

    # 自动整理项是否有改动，如果有改动进度重置到阶段2
    if save_mode["img"] and os.path.exists(file_path + "/img_save_info.json"):
        auto_sort_setting = {"按tag分类": classify_by_tag, "优先tag": prior_tags,
                             "非优先tag聚合": agg_non_prior_tag}
        img_save_info_str = open(file_path + "/img_save_info.json", "r", encoding="utf-8").read()
        img_save_info = json.loads(img_save_info_str)
        if img_save_info["自动整理设置"] != auto_sort_setting:
            os.remove(file_path + "/classified_blogs_info.json")
            os.remove(file_path + "/img_save_info.json")
            print("优先tag发生更改，重置重置到阶段2")

            print("删除上次保存的图片", end="   ")
            shutil.rmtree(file_path + "/img")
            print("删除完成")

    # 运行

    # 阶段1，信息获取和整理 format_fav_info.json存在为这一阶段结束的标志
    step1_start_time = time.time()
    str1 = ""
    if mode == "like1" or mode == "like2":
        str1 = "喜欢"
    elif mode == "share":
        str1 = "推荐"
    elif mode == "tag":
        str1 = "tag"
    print("阶段1：{}页面信息获取与信息整理".format(str1))
    if not os.path.exists(file_path + "/format_blogs_info.json"):
        save_all_fav(url, mode, file_path, login_info, start_time)
        fav_str = open(file_path + "/blogs_info", "r", encoding="utf-8").read()
        fav_info = fav_str.split("\n\nsplit_line\n\n")
        fav_info = fav_info[0:-1]

        print("\n开始解析")

        infor_formater(fav_info, fav_str, mode, file_path, start_time, min_hot, print_level)
        step1_finish_time = time.time()
        print("解析完成")
        print("阶段1耗时 {} 分钟".format(round((step1_finish_time - step1_start_time) / 60), 2))
    else:
        print("阶段1在之前的运行中已完成")
    blogs_info = json.loads(open(file_path + "/format_blogs_info.json", encoding="utf-8").read())

    # 阶段2，分类，删除classified_fav_info.json以重启该阶段
    step2_start_time = time.time()
    print("\n" + "=====================" * 10 + "\n阶段2：博客分类，增加按自动整理选项增加需要的信息")
    if not os.path.exists(file_path + "/classified_blogs_info.json"):
        blogs_info = update_key_tag(blogs_info, classify_by_tag, prior_tags, agg_non_prior_tag)
        classified_blogs = classify(blogs_info)

        with open(file_path + "/classified_blogs_info.json", "w", encoding="utf-8", errors="ignore") as op:
            op.write(json.dumps(classified_blogs, ensure_ascii=False, indent=4))
        step2_finish_time = time.time()
        print("阶段2完成，耗时 {} 秒".format(step2_finish_time - step2_start_time))
    else:
        print("阶段2在之前的运行中已完成")

    classified_blogs = json.loads(open(file_path + "/classified_blogs_info.json", "r", encoding="utf-8").read())

    # 3 对博客类型和tag进行统计
    # types = ["img", "article", "text", "long article"]
    types_str = {"img": "图片博客", "article": "文章博客（带标题）", "text": "文字博客（无标题）", "long article": "长文章",
                 "all": "全部博客"}

    print("\n" + "======================" * 20 + "\n博客类型统计：")
    type_count = count_type(classified_blogs)
    for type1 in type_count:
        print("{} {} 篇".format(types_str[type1], type_count[type1]))
    print("{} {} 篇".format("共计", len(blogs_info)))

    tag_count = {}
    for type1 in classified_blogs:
        tag_count[type1] = count_tag(classified_blogs[type1])
    tag_count["all"] = count_tag(blogs_info)
    filt_tag_count = {}
    for type1 in tag_count:
        filt_dic = {}
        for tag in tag_count[type1]:
            if tag_count[type1][tag] > tag_filt_num:
                filt_dic[tag] = tag_count[type1][tag]
        filt_tag_count[type1] = filt_dic

    print("\n" + "=====================" * 20 + "\ntag 统计：\n" + "-----------------------" * 100)
    for type1 in tag_count:
        print("{}共计tag {} 个，出现次数超过 {} 的tag {} 个".format(types_str[type1], len(tag_count[type1]), tag_filt_num,
                                                        len(filt_tag_count[type1])))
        print("各tag出现次数统计:\n{}".format(filt_tag_count[type1]))
        print("{}".format(list(filt_tag_count[type1].keys())))
        print("-------------------" * len(tag_count["img"]))

    print()
    if not os.path.exists(base_path + "/prior_tags.txt"):
        with open(base_path + "/prior_tags.txt", "w", encoding="utf-8") as op:
            op.write("\n".join(tag_count["all"].keys()))
        print()

    print("======================" * 10)
    is_on = lambda x: "启动" if x else "未启动"
    print("\n自动整理选项：\n按tag整理至同文件夹内\t{}\n指定优先tag\t{}\n非优先tag聚合\t{}".format(is_on(classify_by_tag), is_on(prior_tags),
                                                                          is_on(agg_non_prior_tag)))
    # print("优先tag： {}".format(prior_tags))
    stop_key = input("\n可以现在退出对自动整理选项进行修改，并删除classified_fav_info.json以重新执行阶段2，输入ok以继续\n")
    if not stop_key == "ok":
        exit()
    print("====================" * 20 + "\n进入保存阶段")

    # 阶段4 保存文件
    # 保存文章
    if save_mode["article"]:
        print("\n\n------------开始保存文章------------")
        # 如果文章文件夹已经存在，重新开始保存，删除并重建文件夹
        if os.path.exists(file_path + "/article"):
            print("删除上次运行保存的文章")
            shutil.rmtree(file_path + "/article")
        os.makedirs(file_path + "/article")
        if classified_blogs["article"]:
            save_article(classified_blogs["article"], file_path, classify_by_tag, prior_tags,
                         agg_non_prior_tag, save_img_in_text, print_level)
        else:
            print("无文章")
    # 保存文本
    if save_mode["text"]:
        print("\n\n------------开始保存文本-----------")
        if os.path.exists(file_path + "/text"):
            shutil.rmtree(file_path + "/text")
            print("删除上次运行保存的文本")
            os.makedirs(file_path + "/text")
        if classified_blogs["text"]:
            save_text(classified_blogs["text"], file_path, save_img_in_text)
        else:
            print("无文本")
    # 保存长文章
    if save_mode["long article"]:
        print("\n\n------------开始保存长文章------------")
        if os.path.exists(file_path + "/long article"):
            shutil.rmtree(file_path + "/long article")
            print("删除上次运行保存的长文章")
            os.makedirs(file_path + "/long article")
        if classified_blogs["long article"]:
            save_long_article(classified_blogs["long article"], file_path, save_img_in_text)
        else:
            print("无长文章")

    # 保存图片
    auto_sort_setting = {"按tag分类": classify_by_tag, "优先tag": prior_tags,
                         "非优先tag聚合": agg_non_prior_tag}
    step3_start_time = time.time()
    if save_mode["img"]:
        print("\n\n------------准备保存图片------------")
        # 查看是否有上次的保存进度，如果没有新建一个，有则直接读取
        if not os.path.exists(file_path + "/img_save_info.json"):
            img_save_info = {"图片博客总数": len(classified_blogs["img"]), "已保存": 0, "自动整理设置": auto_sort_setting}
            print("新建保存进度 {}".format(img_save_info))
            with open(file_path + "/img_save_info.json", "w", encoding="utf-8") as op1:
                op1.write(json.dumps(img_save_info, ensure_ascii=False, indent=4))
        else:
            img_save_info_str = open(file_path + "/img_save_info.json", "r", encoding="utf-8").read()
            img_save_info = json.loads(img_save_info_str)
            print("读取到上次的进度 {}".format(img_save_info))

        # 自动整理设置有变化的话重置文件，删除已保存图片，重新得到key tag
        save_img(classified_blogs["img"], file_path, img_save_info, classify_by_tag, prior_tags,
                 agg_non_prior_tag, print_level)
        print("所有图片保存完成")
    step3_finish_time = time.time()
    print("本次运行中保存耗时 {} 分钟".format(round((step3_finish_time - step3_start_time) / 60), 2))

    # 运行结束，退出
    while 1:
        str1 = input("本次运行已结束，输入 yes 以删除进度文件以重置整个程序，或输入 no 退出\n")
        file_list = []
        if str1 == "yes":
            path_list = os.listdir(file_path)
            for path1 in path_list:
                if os.path.isfile(file_path + "/" + path1):
                    file_list.append(path1)
            for path2 in file_list:
                os.remove(file_path + "/" + path2)
                print("删除文件 {}".format(file_path + "/" + path2))
            break
        elif str1 == "no":
            break


if __name__ == '__main__':
    # 启动程序前请先填写 login_info.py
    # 基础设置  -------------------------------------------------------- #
    url = "https://ishtartang.lofter.com/tag/%E5%88%BA%E5%AE%A2%E4%BF%A1%E6%9D%A1"
    # 运行模式
    mode = "like2"

    # 保存哪些内容，1为开启，0为关闭
    # article-文章  text-文本   long article-长文章     img-保存图片
    save_mode = {"article": 1, "text": 1, "long article": 1, "img": 1}

    # 自动整理设置    --------------------------------------------------- #
    # 按tag分类：0关闭 1启动
    classify_by_tag = 1

    # 优先tag:该项不为空时为启动该功能，未启动按tag分类时该功能无效
    prior_tags = []
    # 非优先tag聚合：
    agg_non_prior_tag = 0

    from login_info import login_auth, login_key

    # 最早时间指定 格式：2019-10-1
    start_time = "2024-06-01"
    # 上次运行时间 2020-11-14

    # tag模式的最低热度限制  --------------------------------------------- #
    min_hot = 0

    # 其他设置  ------------------- -------------------------------------- #

    # 保存 文章/长文章/文本 中包含的图片，lofter是可以插图片连接的所以图片不一定是lofter的图片，这个功能有翻车的可能性
    save_img_in_text = 1

    # tag统计输出过滤，只显示出现过多少次以上的tag。
    tag_filt_num = 50

    # 输出等级，等级1输出的信息较多，等级0较少，非调试建议0
    print_level = 0

    # 文件设置  -------------------------------------------------------- #
    # 运行中产生的文件和保存文件的存放路径
    file_path = "./dir"

    # 运行
    login_info = {"login_key": login_key, "login auth": login_auth}
    run(url, mode, save_mode, classify_by_tag, prior_tags, agg_non_prior_tag, login_info, start_time, tag_filt_num,
        min_hot, print_level, save_img_in_text, file_path)
