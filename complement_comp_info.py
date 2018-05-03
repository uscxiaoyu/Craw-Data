# coding=utf-8
from urllib import request, parse
from bs4 import BeautifulSoup
from pymongo import MongoClient
import datetime
import ssl

context = ssl._create_unverified_context()  # 不验证网页安全性

class Single_proj_craw:

    def __init__(self, p_id):
        self.User_Agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:59.0) Gecko/20100101 Firefox/59.0'
        self.Host = 'z.jd.com'
        self.p_id = p_id
        self.craw_time = datetime.datetime.now()

        url_1 = 'http://z.jd.com/project/details/%s.html' % self.p_id
        req = request.Request(url_1)
        req.add_header('User-Agent', self.User_Agent)
        req.add_header('Host', self.Host)
        with request.urlopen(req, context=context) as f:
            self.isDirected = url_1 == f.geturl()  # 是否发生重定向，如果发生重定向，则说明项目失败；双重保护
            rawhtml = f.read().decode('utf-8')
            self.h_soup = BeautifulSoup(rawhtml, 'html.parser')

    def company_data(self):
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

        return {'公司名称': company_name, '公司地址': company_address, '公司工作时间': company_hours, '公司电话': company_phone}

if __name__ == '__main__':
    client = MongoClient('localhost', 27017)
    db = client.moniter_crowdfunding
    project = db.projects  # 监测中的collection
    pid_set = [x['_id'] for x in list(project.find({}, projection={'_id': True}))]
    for p_id in pid_set:
        try:
            s_project = Single_proj_craw(p_id)
            update_info = s_project.company_data()
            project.update_one({'_id': p_id}, {'$set': update_info})
            print(p_id, '公司名称: %s' % update_info['公司名称'])
        except Exception as e:
            print(p_id, '众筹失败')
