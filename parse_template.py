from lxml.html import fromstring, tostring
from html.parser import HTMLParser

"""
//div[@class="content"]			基本版		有标题	http://yangliu12.lofter.com/post/30ee0643_1c98d95fa
//div[@class="cont"]/div[@class="text"]	作者头像在上	有标题	http://sxhyl.lofter.com/post/1e77aca2_1c6d7acdc
//div[@class="cont"]/div[@class="text"]	左侧小菜单	有标题	http://bmdxc.lofter.com/post/3d8916_1c823c9f3
//div[@class="txtcont"]			左侧小菜单	无标题	http://cersternay.lofter.com/post/1d57590b_ee734b04
//div[@class="txtcont"]			作者头像在上	无标题	http://one-four-one.lofter.com/post/1e90aa4f_1c93940ea
//div[@class="text"]			左侧小菜单	有标题	http://anisette642.lofter.com/post/30f2af97_1c99476b6

//div[@class="text"]			左侧小菜单	无标题	https://imakuf.lofter.com/post/1f7d9e_1c7651049
//div[@class="text"]			作者头像在上	无标题	https://heiyulan.lofter.com/post/1e59a3_1c8d1df2b

感觉像自己排的页面
//div[@class="cont"]/div[@class="text f-cb"]	作者头像在上	有标题	http://canggoucelia.lofter.com/post/1ecb7f38_f911873
//div[@class="text f-cb"]

//div[@class="content"]			作者头像在右	无标题	https://yujochen.lofter.com/post/1f9b2521_1c9936caa


"""


# 不到h标签的排版会比较好看，所以优先匹配没有标题的，标题会在正式匹配种被去掉
# 到h标签能确保没有标题，但排版不能还原原文档


# 通用模板，会爬到些别的
def all_purpose_template(parse, title):
    lines = parse.xpath('/html//text()')
    content = "".join(lines)
    content = content.split(title, 2)[2].split("评论")[0]
    return content


# 模板1 lofter初始模板 http://yangliu12.lofter.com 有标题
def template1(parse):
    # line = parse.xpath('//div[@class="content"]//p//text()')
    lines = parse.xpath('//div[@class="content"]/div[@class="text"]//text()')
    content = "".join(lines)
    return content


# 模板2 http://sxhyl.lofter.com/post/1e77aca2_1c6d7acdc 有标题
def template2(parse):
    lines = parse.xpath('//div[@class="cont"]/div[@class="text"]//text()')
    content = "".join(lines)
    return content


# 模板3 https://bmdxc.lofter.com/post/3d8916_1c9a35a4b，有标题 跟2很像，但是标签有点问题
def template3(parse):
    # lines = parse.xpath('//div[@class="cont"]//text()')
    lines = parse.xpath('//div[@class="cont"]/div[@class]//text()')
    content = "".join(lines).split("评论")[0]
    return content


# 模板4 http://cersternay.lofter.com/post/1d57590b_ee734b04 无标题
def template4(parse):
    lines = parse.xpath('//div[@class="txtcont"]//text()')
    content = "".join(lines)
    return content


# 模板5 https://imakuf.lofter.com/post/1f7d9e_1c7651049 无标题
def template5(parse):
    lines = parse.xpath('//div[@class="text"]//text()')
    content = "".join(lines)
    return content


# 模板6 https://anisette642.lofter.com/post/30f2af97_1c9a05b43 有标题
def template6(parse):
    lines = parse.xpath('//div[@class="text"]/p/text()')
    contetn = "\n\n".join(lines)
    return contetn


def matcher(parse, title):
    template_id = 0
    if template1(parse) != "":
        template_id = 1
    elif template2(parse) != "":
        template_id = 2
    elif template3(parse) != "":
        template_id = 3
    elif template4(parse) != "":
        template_id = 4
    elif template5(parse) != "":
        template_id = 5
    elif template6(parse) != "":
        template_id = 6
    return template_id


def get_content(parse, template_id, title):
    content = ""
    if template_id == 1:
        content = template1(parse)
        content = content.replace(title, "", 1)
    if template_id == 2:
        content = template2(parse)
        content = content.replace(title, "")
    if template_id == 3:
        content = template3(parse)
        content = content.replace(title, "")
    if template_id == 4:
        content = template4(parse)
    if template_id == 5:
        content = template5(parse)
    if template_id == 6:
        content = template6(parse)
    if template_id == 0:
        content = all_purpose_template(parse, title)
        content = content.replace("    ", "").replace("\t", "")
    content = content.strip()
    return content
