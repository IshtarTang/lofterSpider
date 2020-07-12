import os
import json
import time

if __name__ == '__main__':
    f = open("./dir/prior_tags.txt","r",encoding="utf-8").read()
    f_list = f.split("\n")
    a_list = []
    for a in f_list:
        k = a.replace("\u3000"," ")
        a_list.append(a)
    print(len(a_list))
    print(a_list)