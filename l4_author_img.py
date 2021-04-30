import re
import os
import time
import json
import random
import requests
from urllib.parse import unquote
from lxml.html import etree
import useragentutil

session = requests.session()


def post_content(url, data, head):
    session.headers = head
    response = session.post(url, data=data)
    content = response.content.decode("utf-8")
    return content


# 检查文件是否有内容，有返回文件第一行，没有返回0
def is_file_in(file_name):
    file = open(file_name, "r")
    first_line = file.readline().replace("\n", "")
    file.close()
    if first_line:
        return first_line
    else:
        return 0


# 返回文件内容
def get_file_contetn(file_name):
    file = open(file_name, "r")
    file_content = json.load(file)
    file.close()
    return file_content


# 更新文件
def file_update(file_name, list):
    with open(file_name, "w") as op:
        op.write(json.dumps(list, indent=0))


# 构建post请求需要的data
def make_data(authorId, query_num):
    data = {
        "callCount": "1",
        "scriptSessionId": "${scriptSessionId}187",
        "httpSessionId": "",
        "c0-scriptName": "ArchiveBean",
        "c0-methodName": "getArchivePostByTime",
        "c0-id": "0",
        "c0-param0": "boolean:false",
        "c0-param1": "number:" + authorId,
        "c0-param2": "number:" + str(round(time.time() * 1000)),
        "c0-param3": "number:" + str(query_num),
        "c0-param4": "boolean:false",
        "batchId": "918906"
    }
    return data


# 构建请求头
def make_head(author_url):
    header = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/79.0.3945.88 Safari/537.36",
        "Host": author_url.split("//")[1].replace("/", ""),
        "Origin": author_url,
        "Referer": author_url + "/view"
    }
    return header


# 检查时间是否早于设定的时间，早于返回True，不早于返回flase
def is_stamp_early(timestamp, start_time):
    timestamp = int(timestamp) / 1000
    # 字符串转时间戳
    start_time = time.strptime(start_time, "%Y-%m-%d")
    start_timestamp = time.mktime(start_time)

    # 博客时间戳早于设定时间
    if timestamp < start_timestamp:
        return True
    else:
        return False


# 检查时间是否晚于设定的时间，晚于返回True，不晚于返回flase
def is_stamp_late(timestamp, end_time):
    timestamp = int(timestamp) / 1000
    end_time = time.strptime(end_time, "%Y-%m-%d")
    end_timestamp = time.mktime(end_time)

    # 博客时间戳晚于设定时间
    if timestamp > end_timestamp:
        return True
    else:
        return False


def img_fliter(imgs_url):
    fliterd_imgs_url = []
    for img_url in imgs_url:
        # 按链接格式过滤掉头像图片和推荐图片
        if "16y16" in img_url or "&amp;" in img_url or "64x64" in img_url or "16x16" in img_url:
             continue
        # 删除图片链接中的大小参数，获取时会默认最高画质
        img_url = img_url.split("imageView")[0]
        # img_url = re.sub(r"imageView&thumbnail=\d*x\d*&quality=\d+&", "", img_url)
        # 去重
        if img_url not in fliterd_imgs_url:
            fliterd_imgs_url.append(img_url)
    return fliterd_imgs_url


# tag过滤，如果博客中tag包含目标tag返回True，否则返回flase
# 如果博客没有任何tag，mode为in时该篇博客会保留，mode为out时则会被过滤掉
def tag_filter(blog_tags, target_tags, mode):
    if not blog_tags:
        if mode == "in":
            return True
        else:
            return False
    for tag in blog_tags:
        if tag in target_tags:
            return True
    return False


# 获取归档页面信息
def parse_archive_page(url, header, data, author_url, query_num, start_time, end_time):
    all_blog_info = []

    while True:
        print("获取归档页面信息，当前请求的时间戳参数为 %s" % data["c0-param2"])
        page_data = post_content(url=url, data=data, head=header)
        # 正则匹配出每条博客的信息并增加到数组all_blog_info
        new_blogs_info = re.findall(r"s[\d]*.blogId.*\n.*noticeLinkTitle", page_data)
        all_blog_info += new_blogs_info
        # 当返回的博客数不等于请求参数中的query_num时说明已经获取到所有的博客信息，跳出循环
        if not len(new_blogs_info) == query_num:
            break
        # 如果设定了开始时间，且最后一个时间戳小于设定的时间，跳出循环
        if start_time:
            if is_stamp_early(data["c0-param2"].split(":")[1], start_time):
                break
        # 正则匹配本页最后一条博客信息的时间戳，用于下个请求data中的参数
        data['c0-param2'] = 'number:' + str(re.search('s%d\.time=(.*);s.*type' % (query_num - 1), page_data).group(1))
        time.sleep(random.randint(1, 2))

    # 过滤和整理博客信息，整理后每条结构为{"blog_url": "http://***","time": "20**-**-**","img_url": "http://***"}
    parsed_blog_info = []
    blog_num = 0
    for blog_info in all_blog_info:
        # 时间戳
        timestamp = re.search(r's[\d]*.time=(\d*);', blog_info).group(1)
        # 只爬取设定时间内，时间线时从新到旧，如果早于该时间则直接跳出循环，如果晚于则跳过这一次循环，没有设定则全部爬取。
        if start_time:
            if is_stamp_early(timestamp, start_time):
                break
        if end_time:
            if is_stamp_late(timestamp, end_time):
                continue
        blog_info_dic = {}
        blog_num += 1

        # 获取缩略图链接，过滤没有图片的博客链接
        try:
            blog_info_dic["img_url"] = re.findall(r'[\d]*.imgurl="(.*?)"', blog_info)[0]
        except:
            blog_info_dic["img_url"] = ""
        if not blog_info_dic["img_url"]:
            continue

        # 博客的编号 比如https://lindujiu.lofter.com/post/423a9c_1c878d5e6 的 423a9c_1c878d5e6
        blog_index = re.search(r's[\d]*.permalink="(.*)"', blog_info).group(1)
        blog_info_dic["blog_url"] = author_url + "/post/" + blog_index

        # 获取时间
        time_local = time.localtime(int(int(timestamp) / 1000))
        dt_time = time.strftime("%Y-%m-%d", time_local)
        blog_info_dic["time"] = dt_time

        parsed_blog_info.append(blog_info_dic)

    print("归档页面解析完毕，共获取博客链接数%d，带图片博客数%d" % (blog_num, len(parsed_blog_info)))
    return parsed_blog_info


# 用来判断两条博客发布时间是否相同的
pre_page_last_img_info = {"last_file_time": '', "index": ''}


# 从博客页面获取图片信息
def parse_blogs_info(blogs_info, parsed_blogs_info, author_name, author_ip, target_tags, tags_filter_mode,
                     file_update_interval):
    """
    :param blogs_info: 未解析的博客信息
    :param parsed_blogs_info: 已解析完的博客信息
    :param author_name: 作者名
    :param author_ip 作者的lofter三级域名
    :param target_tags 保留带有哪些tag的博客
    :param tags_filter_mode 博客过滤方式
    :return: 无

    解析完成的图片信息会写入./dir/imgs_info.json
    """
    global pre_page_last_img_info
    imgs_info = get_file_contetn("./dir/author_img_file/imgs_info.json")  # 上次获取到的图片信息
    parsed_num = len(parsed_blogs_info)

    # 循环len(blogs_info)次，每次解析blogs_info的第一元素，解析完后删除，定时将blogs_info刷新到文件中，以保证中途失败后能继续爬取
    for blog_num in range(len(blogs_info)):
        blog_url = blogs_info[0]["blog_url"]
        img_time = blogs_info[0]["time"]
        print("博客 %s 开始解析" % blog_url, end="  ")
        content = requests.get(blog_url, headers=useragentutil.get_headers()).content.decode("utf-8")

        blog_tags = re.findall(r'"http[s]{0,1}://.*?.lofter.com/tag/(.*?)"', content)
        blog_tags = list(map(lambda x: unquote(x, "utf-8").replace("\xa0", " "), blog_tags))

        if target_tags:
            if not tag_filter(blog_tags, target_tags, tags_filter_mode):
                del blogs_info[0]
                parsed_num += 1
                print("该篇博客被过滤掉，剩余%d" % (len(blogs_info)))
                # 文件刷新
                if (blog_num % file_update_interval == 0) or len(blogs_info) == 0:
                    file_update("./dir/author_img_file/blogs_info.json", blogs_info)
                    file_update("./dir/author_img_file/imgs_info.json", imgs_info)
                    file_update("./dir/author_img_file/blogs_info_parsed.json", parsed_blogs_info)
                    print("文件刷新")
                    time.sleep(random.randint(1, 2))
                continue

        # 不同作者主页会有不同页面结构，所以没有使用xpath而是直接用正则匹配出所有的图片链接，其中会包括一些评论头像和推荐图片
        # 大概9月前的图片链接格式是nosdn，9月之后是imglf
        # imgs_url = re.findall('"(http[s]{0,1}://imglf\d{0,1}.nosdn\d*.[0-9]{0,3}.net.*?)"', content)
        imgs_url = re.findall('"(http[s]{0,1}://imglf\d{0,1}.lf\d*.[0-9]{0,3}.net.*?)"', content)

        # 过滤后为空说明没有获取到有效图片
        if not img_fliter(imgs_url):
            print("使用旧正则表达式", end="\t")
            imgs_url = re.findall('"(http[s]{0,1}://imglf\d.nosdn\d*.12\d.net.*?)"', content)

        # 去除重复链接
        filter_imgs_url = []
        for img_url in imgs_url:
            if img_url not in filter_imgs_url:
                filter_imgs_url.append(img_url)
        imgs_url = filter_imgs_url
        
        # 判断跟上一博客的发表日期是否相同，如果是的话文件下标接上次的增加
        img_index = 0
        if img_time == pre_page_last_img_info["last_file_time"]:
            img_index = pre_page_last_img_info["index"]

        # 过滤图片链接
        imgs_url = img_fliter(imgs_url)

        # 整理图片信息，用于下一步保存
        count = 0
        for img_url in imgs_url:
            # 判断图片类型是jpg png还是gif
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
            img_index += 1
            img_info["pic_name"] = author_name + "[" + author_ip + "] " + img_time + "(" + str(
                img_index) + ")." + img_type
            imgs_info.append(img_info)
            count += 1

            # 用于验证下一条博客是不是同一天发的
            pre_page_last_img_info["last_file_time"] = img_time
            pre_page_last_img_info["index"] = img_index

        # next_some_time用于判断跟下一篇博客发布时间是否相同，相同则不能刷新文件，防止相同时程序中断pre_page_last_img_info数据无法传递
        try:
            if blogs_info[0]["time"] == blogs_info[1]["time"]:
                next_some_time = 1
            else:
                next_some_time = 0
        except:
            next_some_time = 0

        parsed_num += 1
        parsed_blogs_info.append(blogs_info[0])
        del blogs_info[0]
        print("解析完成，获取到图片链接%d，总获取图片数%d，已解析完成%d个链接（本次运行中已解析%d个链接），剩余%d" % (
            count, len(imgs_info), parsed_num, blog_num + 1, len(blogs_info)))

        # print(imgs_url)
        # print("--------"*10)

        # 按文件数目为间隔，将未解析博客、解析出的图片信息、已解析的博客 刷新到文件中
        if (blog_num % file_update_interval == 0 and not next_some_time) or len(blogs_info) == 0:
            file_update("./dir/author_img_file/blogs_info.json", blogs_info)
            file_update("./dir/author_img_file/imgs_info.json", imgs_info)
            file_update("./dir/author_img_file/blogs_info_parsed.json", parsed_blogs_info)
            print("文件刷新")
            time.sleep(random.randint(1, 2))

    with open("./dir/author_img_file/blogs_info.json", "w") as op:
        op.write("finished")


# 图片下载
def download_img(imgs_info, imgs_info_saved, author_name, author_ip, file_update_interval):
    """
    :param imgs_info: 图片信息
    :param imgs_info_saved: 已完成保存的图片信息
    :param author_name: 作者名
    :param author_ip 作者的lofter三级域名
    :return:无
    """
    author_name_in_filename = author_name.replace("/", "&").replace("|", "&").replace("\\", "&"). \
        replace("<", "《").replace(">", "》").replace(":", "：").replace('"', '”').replace("?", "？"). \
        replace("*", "·").replace("\n", "").replace("(", "（").replace(")", "）")
    dir_path = "./dir/img/" + author_name_in_filename + "[" + author_ip + "]"
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    save_num = len(imgs_info_saved)
    for img_index in range(len(imgs_info)):
        pic_name = imgs_info[0]["pic_name"]
        pic_name_in_filename = pic_name.replace("/", "&").replace("|", "&").replace("\r", " ").replace(
            "\\", "&").replace("<", "《").replace(">", "》").replace(":", "：").replace('"', '”').replace("?", "？") \
            .replace("*", "·").replace("\n", "").replace("(", "（").replace(")", "）").strip()

        pic_url = imgs_info[0]["img_url"]
        img_path = dir_path + "/" + pic_name_in_filename
        print("获取图片 %s" % (pic_url))
        content = requests.get(pic_url, headers=useragentutil.get_headers()).content
        with open(img_path, "wb") as op:
            op.write(content)

        save_num += 1
        imgs_info_saved.append(imgs_info[0])
        del imgs_info[0]

        print("图片已保存，共保存图片%d (本次运行已保存%d)，余%d" % (save_num, img_index + 1, len(imgs_info)))

        if img_index % file_update_interval == 0 or len(imgs_info) == 0:
            file_update("./dir/author_img_file/imgs_info.json", imgs_info)
            file_update("./dir/author_img_file/imgs_info_saved.json", imgs_info_saved)
            time.sleep(1)
            print("文件刷新")
    with open("./dir/author_img_file/imgs_info.json", "w")as op:
        op.write("finished")


# 运行时需要文件创建和删除
def deal_file(action):
    dir_path = "./dir/author_img_file"
    blog_info_file = dir_path + "/blogs_info.json"
    img_info_file = dir_path + "/imgs_info.json"
    blogs_info_parsed_file = dir_path + "/blogs_info_parsed.json"
    img_info_file_saved = dir_path + "/imgs_info_saved.json"

    if action == "init":
        print("检查运行所需的文件")
        if not os.path.exists(dir_path):
            os.mkdir(dir_path)
            print("创建文件夹: %s" % dir_path)
        if not os.path.exists(blog_info_file):
            with open(blog_info_file, "w") as op1:
                op1.write("")
            print("创建文件: %s" % blog_info_file)
        for file_path in [img_info_file, blogs_info_parsed_file, img_info_file_saved]:
            if not os.path.exists(file_path):
                with open(file_path, "w")as op:
                    op.write("[]")
                print("创建文件: %s" % file_path)

    if action == "del":
        for file_name in [blog_info_file, img_info_file, blogs_info_parsed_file, img_info_file_saved]:
            os.remove(file_name)
            print("已删除%s" % file_name)


# 整理各种参数，启动程序
def run(author_url, start_time, end_time, target_tags, tags_filter_mode, file_update_interval):
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
    data = make_data(author_id, query_num)
    head = make_head(author_url)

    try:
        print("作者名%s,lofter ip %s,主页链接 %s" % (author_name, author_ip, author_url))
    except:
        print("作者名中有异常符号,无法显示,lofter ip %s,主页链接 %s" % (author_ip, author_url))

    deal_file("init")
    dir_path = "./dir/author_img_file"
    # 判断博客解析进度
    if is_file_in(dir_path + "/blogs_info.json") == "finished":
        print("所有博客已解析完毕，跳转至图片下载")
    elif is_file_in(dir_path + "/blogs_info.json"):
        blogs_info = get_file_contetn(dir_path + "/blogs_info.json")
        parsed_blogs_info = get_file_contetn(dir_path + "/blogs_info_parsed.json")
        print("读取到上次运行保存的博客信息：未解析博链接%d条，已解析链接%d条，接上次继续运行" % (len(blogs_info), len(parsed_blogs_info)))
        parse_blogs_info(blogs_info, parsed_blogs_info, author_name, author_ip, target_tags, tags_filter_mode,
                         file_update_interval)
    else:
        print("开始获取归档页面数据，链接 %s (不能直接点开)" % archive_url)
        blog_infos = parse_archive_page(url=archive_url, data=data, header=head, author_url=author_url,
                                        query_num=query_num, start_time=start_time, end_time=end_time)
        parsed_blogs_info = get_file_contetn(dir_path + "/blogs_info_parsed.json")
        file_update(dir_path + "/blogs_info.json", blog_infos)
        print("归档页面数据保存完毕,开始解析博客页面")
        parse_blogs_info(blog_infos, parsed_blogs_info, author_name, author_ip, target_tags, tags_filter_mode,
                         file_update_interval)
        print("博客解析完毕，开始图片下载")
    # 判断图片保存进度
    if is_file_in(dir_path + "/imgs_info.json") == "finished":
        print("该作者首页的所有图片已保存完毕，无需操作")
    else:
        imgs_info = get_file_contetn(dir_path + "/imgs_info.json")
        imgs_info_saved = get_file_contetn(dir_path + "/imgs_info_saved.json")
        download_img(imgs_info, imgs_info_saved, author_name, author_ip, file_update_interval)
        print("所有图片保存完毕")

    deal_file("del")
    print("程序运行结束")


if __name__ == "__main__":
    # 一个会出bug的主页 https://silhouette-of-wolf.lofter.com/
    # 作者在头像下放了tag，导致tag过滤失效，所有的内容都会被保存

    # 作者的主页地址   示例 https://ishtartang.lofter.com/   *最后的'/'不能少
    author_url = "https://allkakashi.lofter.com/"


    # ### 自定义部分 ### #

    # 设定爬取哪个时间段的博客，空值为不设定 格式："yyyy-MM-dd"
    start_time = ""
    end_time = ""
    # 指定保留有哪些tag的博客，空值为不过滤
    target_tags = ["卡卡西"]
    # target_tags = ["汉尼拔", "拔杯", "Hannibal", "hannigram", "麦斯米科尔森", "madsmikkslsen"]
    # tag过滤模式，为in时会保留没有任何tag的博客，为out时不保留
    tags_filter_mode = "out"

    # 间隔多久把数据刷新到文件中一次
    file_update_interval = 10

    run(author_url, start_time, end_time, target_tags, tags_filter_mode, file_update_interval)
