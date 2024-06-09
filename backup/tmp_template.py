import re


# �������Ľṹ �����ޣ������Ҳ�����
"""
//div[@class="content"]			������		�б���	http://yangliu12.lofter.com/post/30ee0643_1c98d95fa
//div[@class="cont"]/div[@class="text"]	����ͷ������	�б���	http://sxhyl.lofter.com/post/1e77aca2_1c6d7acdc
//div[@class="cont"]/div[@class="text"]	���С�˵�	�б���	http://bmdxc.lofter.com/post/3d8916_1c823c9f3
//div[@class="txtcont"]			���С�˵�	�ޱ���	http://cersternay.lofter.com/post/1d57590b_ee734b04
//div[@class="txtcont"]			����ͷ������	�ޱ���	http://one-four-one.lofter.com/post/1e90aa4f_1c93940ea
//div[@class="text"]			���С�˵�	�б���	http://anisette642.lofter.com/post/30f2af97_1c99476b6

//div[@class="text"]			���С�˵�	�ޱ���	https://imakuf.lofter.com/post/1f7d9e_1c7651049
//div[@class="text"]			����ͷ������	�ޱ���	https://heiyulan.lofter.com/post/1e59a3_1c8d1df2b

�о����Լ��ŵ�ҳ��
//div[@class="cont"]/div[@class="text f-cb"]	����ͷ������	�б���	http://canggoucelia.lofter.com/post/1ecb7f38_f911873
//div[@class="text f-cb"]

//div[@class="content"]			����ͷ������	�ޱ���	https://yujochen.lofter.com/post/1f9b2521_1c9936caa

//div[contains(@class,'post-ctc box')]/p/text()  https://chuanshoot.lofter.com/


"""


# ����h��ǩ���Ű��ȽϺÿ�����������ƥ��û�б���ģ����������ʽƥ���б�ȥ��
# ��h��ǩ��ȷ��û�б��⣬���Ű治�ܻ�ԭԭ�ĵ�


# ͨ��ģ�壬������Щ���
def all_purpose_template(parse, title, blog_type, join_word=""):
    lines = parse.xpath('/html//text()')
    content = "".join(lines)
    if blog_type == "article":
        title = title.encode("gbk", errors="replace").decode("gbk", errors="replace").replace("?", "")
        content = content.split(title, 2)[2]
        content = re.split("\s����\s", content)[0].encode("utf-8", errors="replace").decode("utf-8", errors="replace")
    else:
        content = content.split("����")[0].encode("utf-8", errors="replace").decode("utf-8", errors="replace")
    return content


# ģ��1 lofter��ʼģ�� http://yangliu12.lofter.com �б���
def template1(parse, join_word=""):
    lines = parse.xpath('//div[@class="content"]/div[@class="text"]//text()')
    content = join_word.join(lines)
    return content


# ģ��2 http://sxhyl.lofter.com/post/1e77aca2_1c6d7acdc �б���
def template2(parse, join_word=""):
    lines = parse.xpath('//div[@class="cont"]/div[@class="text"]//text()')



    content = join_word.join(lines)
    return content


# ģ��3 https://bmdxc.lofter.com/post/3d8916_1c9a35a4b���б��� ��2���񣬵��Ǳ�ǩ�е�����
def template3(parse, join_word=""):
    # lines = parse.xpath('//div[@class="cont"]//text()')
    lines = parse.xpath('//div[@class="cont"]/div[@class]//text()')
    content = "".join(lines).split("����")[0]
    return content


# ģ��4 http://cersternay.lofter.com/post/1d57590b_ee734b04 �ޱ���
def template4(parse, join_word=""):
    lines = parse.xpath('//div[@class="txtcont"]//text()')
    content = join_word.join(lines)
    return content


# ģ��5 https://imakuf.lofter.com/post/1f7d9e_1c7651049 �ޱ���
def template5(parse, join_word=""):
    lines = parse.xpath('//div[@class="text"]//text()')
    content = join_word.join(lines)
    return content


# ģ��6 https://anisette642.lofter.com/post/30f2af97_1c9a05b43 �б���
def template6(parse, join_word=""):
    lines = parse.xpath('//div[@class="text"]/p/text()')
    contetn = (join_word + "\n\n").join(lines)
    return contetn


# 7 https://chuanshoot.lofter.com/ �������Զ�����ҳ
def template7(parse, join_word=""):
    # lines = parse.xpath("//div[contains(@class,'post-ctc box')]/p/text()")
    lines = parse.xpath("//div[contains(@class,'post-ctc box')]//p//text()")
    content = join_word.join(lines)
    return content


def matcher(parse):
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
    elif template7(parse) != "":
        template_id = 7
    return template_id


def get_content(parse, template_id, title, blog_type, join_word=""):
    content = ""
    if template_id == 1:
        content = template1(parse, join_word)
        content = content.replace(title, "", 1)
    if template_id == 2:
        content = template2(parse, join_word)
        content = content.replace(title, "",1)
    if template_id == 3:
        content = template3(parse, join_word)
        content = content.replace(title, "",1)
    if template_id == 4:
        content = template4(parse, join_word)
    if template_id == 5:
        content = template5(parse, join_word)
    if template_id == 6:
        content = template6(parse, join_word)
    if template_id == 7:
        content = template7(parse, join_word)
    if template_id == 0:
        content = all_purpose_template(parse, title, blog_type, join_word)
        content = content.replace("    ", "").replace("\t", "")
    content = content.strip()
    return content
