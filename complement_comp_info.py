# coding=utf-8
from urllib import request, parse
from bs4 import BeautifulSoup
from pymongo import MongoClient
import datetime
import ssl
import re

context = ssl._create_unverified_context()  # 不验证网页安全性

class Single_proj_craw:

    def __init__(self, p_id, category, count_inqury):
        self.User_Agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:59.0) Gecko/20100101 Firefox/59.0'
        self.Host = 'z.jd.com'
        self.p_id = p_id
        self.category = category  # 预热中、众筹中、众筹成功、项目成功
        self.count_inqury = count_inqury  # 访问次数
        self.p_d = re.compile('\d+')
        self.craw_time = datetime.datetime.now()

        url_1 = 'http://z.jd.com/project/details/%s.html' % self.p_id
        req = request.Request(url_1)
        req.add_header('User-Agent', self.User_Agent)
        req.add_header('Host', self.Host)
        with request.urlopen(req, context=context) as f:
            self.isDirected = url_1 == f.geturl()  # 是否发生重定向，如果发生重定向，则说明项目失败；双重保护
            rawhtml = f.read().decode('utf-8')
            self.h_soup = BeautifulSoup(rawhtml, 'html.parser')

        if self.isDirected:
            url_2 = 'http://sq.jr.jd.com/cm/getCount?'
            req = request.Request(url_2)
            req.add_header('User-Agent', self.User_Agent)
            req.add_header('Referer', 'http://z.jd.com/project/details/%s.html' % self.p_id)
            req.add_header('Host', self.Host)

            post_list = [('_', '15242091922'),
                         ('callback', 'jQuery183000564758012421237_1524209188840'),
                         ('key', '1000'),
                         ('pin', ''),
                         ('systemId', self.p_id),
                         ('temp', '0.29549820811900180')]  # 关键在于systemID，即项目编号

            post_data = parse.urlencode(post_list)

            with request.urlopen(req, data=post_data.encode('utf-8')) as f:
                self.j_soup = f.read().decode()

    def basic_data(self):
        div1 = self.h_soup.find_all('div', {'class': 'project-introduce'})[0]
        proj_name = div1.find_all('h1', {'class': 'p-title'})[0].string  # 项目名称
        company_name, company_address, company_phone, company_hours = None, None, None, None  # 先设为None
        try:
            div3 = self.h_soup.find_all('ul', {'class': "contact-box"})[0]
            div3_li = div3.find_all('li')
            for li in div3_li:  # 少数项目没有公司名称和联系地址
                key = li.find('div', {'class': "key"}).contents[1]
                val = li.find('div', {'class': "val"}).string
                if key == '公司名称：':
                    company_name = val  # 公司名称
                elif key == '联系地址：':
                    company_address = val  # 联系地址
                elif key == '官方电话：':
                    company_phone = val  # 官方电话
                elif key == '工作时间：':
                    company_hours = val  # 工作时间
        except IndexError:
            print('No company info')

        return {'项目名称': proj_name, '公司名称': company_name, '公司地址': company_address, '公司工作时间': company_hours,
                '公司电话': company_phone}


