def write_html(html):
    with open("./example.html", "w", encoding="utf-8") as op:
        op.write(html)


# 保存文本
def write_text(file, filename="test.txt", path="."):
    filename = filename.replace("\r", "")
    with open(path + "/" + filename, "w", encoding="utf-8", errors="ignore") as op:
        op.write(file)
