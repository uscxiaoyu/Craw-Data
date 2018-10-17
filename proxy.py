# 仅爬取西刺代理首页IP地址
import ssl
from bs4 import BeautifulSoup
from urllib import request
context = ssl._create_unverified_context()

def get_ip_list(obj):
    ip_text = obj.findAll('tr', {'class': 'odd'})   # 获取带有IP地址的表格的所有行
    ip_list = []
    for i in range(len(ip_text)):
        ip_tag = ip_text[i].findAll('td')
        ip_port = ip_tag[1].get_text() + ':' + ip_tag[2].get_text() # 提取出IP地址和端口号
        ip_list.append(ip_port)

    print("共收集到了{}个代理IP".format(len(ip_list)))
    print(ip_list)
    return ip_list


if __name__ == '__main__':
    url = 'http://www.xicidaili.com/'
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:59.0) Gecko/20100101 Firefox/59.0'}
    req1 = request.Request(url, headers=headers)
    f = request.urlopen(req1, context=context)
    bsObj = BeautifulSoup(f.read(), 'lxml')     # 解析获取到的html
    get_ip_list(bsObj)