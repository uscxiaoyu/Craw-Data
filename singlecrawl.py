from urllib import request, parse
from bs4 import BeautifulSoup
import socket
import datetime
import ssl
import re
import json

context = ssl._create_unverified_context()  # 不验证网页安全性
socket.setdefaulttimeout(15)  # 设置全局超时


class Single_proj_craw:

    def __init__(self, p_id, count_inqury):
        self.User_Agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:60.0) Gecko/20100101 Firefox/60.0'
        self.Host = 'z.jd.com'
        self.p_id = p_id
        self.count_inqury = count_inqury  # 访问次数
        self.craw_time = datetime.datetime.now()
        self.category = False

        # 当前点赞人数、当前关注者数、项目创建时间、项目更新时间
        self.p_praise = re.compile('"praise":(\d+)')
        self.p_focus = re.compile('"focus":(\d+)')
        self.p_createTime = re.compile(
            '"createTime":"(\d+-\d+-\d+ \d+:\d+:\d+)"')
        self.p_updateTime = re.compile(
            '"updateTime":"(\d+-\d+-\d+ \d+:\d+:\d+)"')
        self.p_d = re.compile('\d+')

        url_1 = 'http://z.jd.com/project/details/%s.html' % self.p_id
        req_1 = request.Request(url_1)
        req_1.add_header('User-Agent', self.User_Agent)
        req_1.add_header('Host', self.Host)
        try:
            with request.urlopen(req_1, context=context) as f_1:
                self.isDirected = self.p_id in f_1.geturl()  # 如果p_id不在实际url中，则说明发生了重定向，项目失败
                if self.isDirected:
                    rawhtml = f_1.read().decode('utf-8')
                    self.h_soup = BeautifulSoup(rawhtml, 'html.parser')
                    cat_div = self.h_soup.find('div', {'class': 'project-img'})
                    l_cat = cat_div.i['class'][0]
                    if l_cat == 'zc-orange-preheat':  # 预热中、众筹中、众筹成功、项目成功
                        self.category = '预热中'
                    elif l_cat == 'zc-green-ing':
                        self.category = '众筹中'
                    elif l_cat == 'zc-success':
                        self.category = '众筹成功'
                    elif l_cat == 'xm-success':
                        self.category = '项目成功'

                    url_2 = 'http://sq.jr.jd.com/cm/getCount?'
                    req_2 = request.Request(url_2)
                    req_2.add_header('User-Agent', self.User_Agent)
                    req_2.add_header(
                        'Referer', 'http://z.jd.com/project/details/%s.html' % self.p_id)
                    req_2.add_header('Host', self.Host)
                    post_list = [('_', '15242091922'),
                                 ('callback', 'jQuery183000564758012421237_1524209188840'),
                                 ('key', '1000'),
                                 ('pin', ''),
                                 ('systemId', self.p_id),
                                 ('temp', '0.29549820811900180')]  # 关键在于systemID，即项目编号
                    post_data = parse.urlencode(post_list)
                    with request.urlopen(req_2, data=post_data.encode('utf-8')) as f_2:
                        self.j_soup = f_2.read().decode()
                else:
                    self.category = "重定向"
        except socket.timeout as e:
            self.category = "超时"
            print(f"  {self.p_id}网页获取出错: {e}")

    def basic_data(self):
        # (1)项目信息
        div1 = self.h_soup.find_all('div', {'class': 'project-introduce'})[0]
        proj_name = div1.find_all('h1', {'class': 'p-title'})[0].string  # 项目名称

        div1_2 = div1.find_all('p', {'class': "p-target"})[0]
        time_span = div1_2.find_all('span', {'class': 'f_red'})[
            0].string.strip()  # 提取截止日期
        time_span = int(time_span)  # 转化数字格式
        target_fund = div1_2.find_all('span', {'class': 'f_red'})[
            1].get_text()[1:]  # 目标金额

        s = self.h_soup.find_all('div', {'class': "tab-share-l"})
        sort_name = s[0].a['data-attr']  # 项目所属类别

        # (2)发起人信息
        div2 = self.h_soup.find_all('div', {'class': "promoters-name"})[0]
        prom_href = div2.find_all('a')[0]['href']  # 发起人href
        prom_name = div2.find_all('a')[0]['title']  # 发起人名称

        # (3)公司信息
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

        # (4)各档支持信息
        div4 = self.h_soup.find_all('div', {'class': "box-grade "})
        indiv_info = {}
        for i, d in enumerate(div4):
            sup_price = d.find_all(
                'div', {'class': "t-price"})[0].span.string.strip()  # 支持价位
            d_1 = d.find_all('div', {'class': "box-content"})
            lim_num = d_1[0].find_all(
                'span', {'class': "limit-num"})[0].string  # 限制人数
            redound_info = d_1[0].find_all(
                'p', {'class': "box-intro"})[0].string.strip()  # 回报内容
            deliver_info = d_1[0].find_all(
                'p', {'class': "box-item"})[1].get_text()  # 发货时间
            indiv_info[str(i)] = {'sup_price': int(sup_price),
                                  'lim_num': lim_num,
                                  'redound_info': redound_info,
                                  'deliver_info': deliver_info}

        return {'项目名称': proj_name, '目标金额': int(target_fund), '众筹期限': time_span,
                '所属类别': sort_name, '发起人链接': prom_href, '发起人名称': prom_name,
                '公司名称': company_name, '公司地址': company_address, '公司工作时间': company_hours,
                '公司电话': company_phone, '各档基础信息': indiv_info}

    def update_data(self):
        # 当前筹集金额、当前进度、当前支持人数
        div1 = self.h_soup.find_all('div', {'class': 'project-introduce'})[0]
        try:
            div1_1 = div1.find_all('p', {'class': "p-progress"})[0]
            now_percent = div1_1.find_all('span', {'class': "fl percent"})[
                0].string[4:-1]  # 当前进度
            now_supporters = div1_1.find_all('span', {'class': "fr"})[
                0].string[:-4]  # 当前支持人数
            now_fund = div1.find_all(
                'p', {'class': "p-num"})[0].get_text()[1:]  # 当前项目筹集金额
        except IndexError:
            now_percent, now_supporters, now_fund = 0, 0, 0
            print('  项目还未开始众筹！')

        if self.category == '众筹中':  # 获取end_time以决定何时获取review信息
            div1 = self.h_soup.find_all(
                'div', {'class': 'project-introduce'})[0]
            div1_2 = div1.find_all('p', {'class': "p-target"})[0]
            end_time = div1_2.find_all('span', {'class': 'f_red'})[
                0].string.strip()  # 提取截止日期
            end_time = '-'.join(self.p_d.findall(end_time))
            self.end_time = datetime.datetime.strptime(
                end_time, '%Y-%m-%d')  # 转化截止日期为标准格式

        # 各档支持信息
        div4 = self.h_soup.find_all('div', {'class': "box-grade "})
        indiv_info = {'爬取时间': self.craw_time}
        for i, d in enumerate(div4):
            now_num_sup = d.find_all(
                'div', {'class': "t-people"})[0].span.string.strip()  # 当前支持人数
            indiv_info[str(i)] = {'now_num_sup': int(now_num_sup)}

        praise = self.p_praise.findall(self.j_soup)[0]  # 点赞人数
        focus = self.p_focus.findall(self.j_soup)[0]  # 关注人数
        try:
            createTime = self.p_createTime.findall(self.j_soup)[0]
            createTime = datetime.datetime.strptime(
                createTime, "%Y-%m-%d %H:%M:%S")  # 项目创建时间

            updateTime = self.p_updateTime.findall(self.j_soup)[0]  # 项目更新时间
            updateTime = datetime.datetime.strptime(
                updateTime, "%Y-%m-%d %H:%M:%S")  # 项目创建时间
        except IndexError:
            createTime = datetime.datetime.now()
            updateTime = datetime.datetime.now()
            print('本项目还没有任何点赞和关注！')

        return {'项目动态信息': {'爬取时间': self.craw_time,
                           '筹集金额': int(now_fund),
                           '完成百分比': float(now_percent),
                           '支持者数': int(now_supporters),
                           '点赞数': int(praise),
                           '关注数': int(focus),
                           '创建时间': createTime,
                           '更新时间': updateTime},
                '各档动态信息': indiv_info}

    def review_data(self):
        url = 'https://sq.jr.jd.com/topic/getTopicList?'
        req = request.Request(url)
        req.add_header('User-Agent', self.User_Agent)
        req.add_header('Referer', 'http://z.jd.com/project/details/%s.html' % self.p_id)
        req.add_header('Host', 'sq.jr.jd.com')
        reviews = {}
        i = 1
        while True:
            post_list = [('_', '1524311286832'),
                         ('callback', 'jQuery183036846271396508157_1524311279519'),
                         ('key', '1000'),
                         ('pageNo', '%d' % i),
                         ('pageSize', '20'),
                         ('serviceType', '1'),
                         ('sort', '1'),
                         ('systemId', '%s' % self.p_id),
                         ('temp', '0.8972247674942638')]  # 关键在于systemID，即项目编号
            post_data = parse.urlencode(post_list)
            f = request.urlopen(
                req, data=post_data.encode('utf-8'), context=context)
            x = f.read().decode()
            json_x = json.loads(x[x.find('{"listResult"'):-1])
            pageBean = json_x['pageBean']
            totalPage = int(pageBean['totalPage'])  # 总页数
            totalRecord = int(pageBean['totalRecord'])  # 总记录数
            # 评论id, 创建时间，点赞数，回复数，内容
            for record in json_x['listResult']:
                reviews[str(record['topicId'])] = record  # 存储所有评论信息
            if totalPage > i:
                i += 1
            else:
                break

        return {'爬取时间': self.craw_time, '总页数': totalPage, '总评论数': totalRecord, '评论详细': reviews}

    def start_craw(self):
        if self.category == '预热中':
            if self.count_inqury == 0:
                return self.basic_data(), self.update_data()
            else:
                return self.update_data()

        elif self.category == '众筹中':
            u_data = self.update_data()  # 必须先执行, self.end_time才有值
            if datetime.datetime.now() < self.end_time - datetime.timedelta(hours=24):
                return u_data
            else:
                return u_data, self.review_data()

        elif self.category == '众筹成功' or self.category == "项目成功":
            return self.review_data()
            

if __name__ == "__main__":
    single_craw = Single_proj_craw("107189", 15)
