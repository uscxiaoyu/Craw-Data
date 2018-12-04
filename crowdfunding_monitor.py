#!/usr/bin/python3.7
from urllib import request, parse
from bs4 import BeautifulSoup
from pymongo import MongoClient
import datetime
import ssl
import re
import time
import json
import random
import frontpage
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr

context = ssl._create_unverified_context()  # 不验证网页安全性


class Single_proj_craw:

    def __init__(self, p_id, count_inqury):
        self.User_Agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:60.0) Gecko/20100101 Firefox/60.0'
        self.Host = 'z.jd.com'
        self.p_id = p_id
        self.count_inqury = count_inqury  # 访问次数
        self.p_d = re.compile('\d+')
        self.craw_time = datetime.datetime.now()
        self.category = False

        url_1 = 'http://z.jd.com/project/details/%s.html' % self.p_id
        req_1 = request.Request(url_1)
        req_1.add_header('User-Agent', self.User_Agent)
        req_1.add_header('Host', self.Host)
        with request.urlopen(req_1, context=context) as f_1:
            self.isDirected = (self.p_id in f_1.geturl())  # 如果p_id不在实际url中，则说明发生了重定向，项目失败
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
                req_2.add_header('Referer', 'http://z.jd.com/project/details/%s.html' % self.p_id)
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

    def basic_data(self):
        # (1)项目信息
        div1 = self.h_soup.find_all('div', {'class': 'project-introduce'})[0]
        proj_name = div1.find_all('h1', {'class': 'p-title'})[0].string  # 项目名称

        div1_2 = div1.find_all('p', {'class': "p-target"})[0]
        time_span = div1_2.find_all('span', {'class': 'f_red'})[0].string.strip()  # 提取截止日期
        time_span = int(time_span)  # 转化数字格式
        target_fund = div1_2.find_all('span', {'class': 'f_red'})[1].get_text()[1:]  # 目标金额

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
            sup_price = d.find_all('div', {'class': "t-price"})[0].span.string.strip()  # 支持价位
            d_1 = d.find_all('div', {'class': "box-content"})
            lim_num = d_1[0].find_all('span', {'class': "limit-num"})[0].string  # 限制人数
            redound_info = d_1[0].find_all('p', {'class': "box-intro"})[0].string.strip()  # 回报内容
            deliver_info = d_1[0].find_all('p', {'class': "box-item"})[1].get_text()  # 发货时间
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
            now_percent = div1_1.find_all('span', {'class': "fl percent"})[0].string[4:-1]  # 当前进度
            now_supporters = div1_1.find_all('span', {'class': "fr"})[0].string[:-4]  # 当前支持人数
            now_fund = div1.find_all('p', {'class': "p-num"})[0].get_text()[1:]  # 当前项目筹集金额
        except IndexError:
            now_percent, now_supporters, now_fund = 0, 0, 0
            print('  项目还未开始众筹！')

        if self.category == '众筹中':  # 获取end_time以决定何时获取review信息
            div1 = self.h_soup.find_all('div', {'class': 'project-introduce'})[0]
            div1_2 = div1.find_all('p', {'class': "p-target"})[0]
            end_time = div1_2.find_all('span', {'class': 'f_red'})[0].string.strip()  # 提取截止日期
            end_time = '-'.join(self.p_d.findall(end_time))
            self.end_time = datetime.datetime.strptime(end_time, '%Y-%m-%d')  # 转化截止日期为标准格式

        # 各档支持信息
        div4 = self.h_soup.find_all('div', {'class': "box-grade "})
        indiv_info = {'爬取时间': self.craw_time}
        for i, d in enumerate(div4):
            now_num_sup = d.find_all('div', {'class': "t-people"})[0].span.string.strip()  # 当前支持人数
            indiv_info[str(i)] = {'now_num_sup': int(now_num_sup)}

        # 当前点赞人数、当前关注者数、项目创建时间、项目更新时间
        p_praise = re.compile('"praise":(\d+)')
        p_focus = re.compile('"focus":(\d+)')
        p_createTime = re.compile('"createTime":"(\d+-\d+-\d+ \d+:\d+:\d+)"')
        p_updateTime = re.compile('"updateTime":"(\d+-\d+-\d+ \d+:\d+:\d+)"')

        praise = p_praise.findall(self.j_soup)[0]  # 点赞人数
        focus = p_focus.findall(self.j_soup)[0]  # 关注人数
        try:
            createTime = p_createTime.findall(self.j_soup)[0]
            createTime = datetime.datetime.strptime(createTime, "%Y-%m-%d %H:%M:%S") # 项目创建时间

            updateTime = p_updateTime.findall(self.j_soup)[0]  # 项目更新时间
            updateTime = datetime.datetime.strptime(updateTime, "%Y-%m-%d %H:%M:%S") # 项目创建时间
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
                         ('temp', '0.8972247674942638')] # 关键在于systemID，即项目编号
            post_data = parse.urlencode(post_list)
            f = request.urlopen(req, data=post_data.encode('utf-8'), context=context)
            x = f.read().decode()
            json_x = json.loads(x[x.find('{"listResult"'):-1])
            pageBean = json_x['pageBean']
            totalPage = int(pageBean['totalPage'])  # 总页数
            totalRecord = int(pageBean['totalRecord'])  # 总记录数
            # 评论id, 创建时间，点赞数，回复数，内容
            for record in json_x['listResult']:
                reviews[str(record['topicId'])] = {'创建时间': record['createTime'],
                                                   '点赞数': int(record['likecount']),
                                                   '回复数': int(record['replys']),
                                                   '评论内容': record['topicContent']}
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
            update_dt = self.update_data()
            if datetime.datetime.now() < self.end_time - datetime.timedelta(hours=12):
                return update_dt
            else:
                return update_dt, self.review_data()

        elif self.category == '众筹成功':
            return self.review_data()


class Collect_craw:

    def __init__(self):
        self.User_Agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:60.0) Gecko/20100101 Firefox/60.0'
        self.Host = 'z.jd.com'
        # 连接MongoDB数据库
        client = MongoClient('localhost', 27017)
        db = client.moniter_crowdfunding
        self.now = datetime.datetime.now()
        self.project = db.projects  # 监测中的collection
        self.failure_project = db.failure_projects  # 众筹失败collection

    def get_pid_list(self, category):  # 获取制定范围页面的项目id
        # info type_xm项目成功, info type_succeed众筹成功, info type_now众筹中, info type_future 预热中
        if category == '预热中':
            status, class_info, sort = '1', 'info type_future', 'zxsx'  #最新上线
        elif category == '众筹中':
            status, class_info, sort = '2', 'info type_now', 'zxsx'
        elif category == '众筹成功':
            status, class_info, sort = '4', 'info type_succeed', 'zxsx'
        elif category == '项目成功':
            status, class_info, sort = '8', 'info type_xm', 'zxsx'

        p_url = 'https://z.jd.com/bigger/search.html'
        pattern = re.compile("\d+")
        pid_list = []
        i = 0
        while True:
            time.sleep(0.1)
            len_pid_list = len(pid_list)
            req = request.Request(p_url)
            # status: 预热中 '1', 众筹中 '2', 众筹成功 '4' 项目成功 '8'
            post_list = [('categoryId', ''), ('keyword', ''), ('page', '%d' % i), ('parentCategoryId', ''),
                         ('productEnd', '-28'), ('sceneEnd', ''), ('sort', sort), ('status', status)]
            post_data = parse.urlencode(post_list)
            req.add_header('User-Agent', self.User_Agent)
            req.add_header('Referer', 'https://z.jd.com/bigger/search.html')
            req.add_header('Host', self.Host)

            with request.urlopen(req, data=post_data.encode('utf-8'), context=context) as f:
                web_data = f.read()
                soup = BeautifulSoup(web_data, 'html.parser')
                ul = soup.find_all('div', {'class': 'l-result'})[0].ul  # 注意，不同状态的class有区别
                li = ul.find_all('li', {'class': class_info})
                for l in li:
                    url = l.find_all('a')[0].get('href')
                    pid = pattern.findall(url)[0]
                    pid_list.append(pid)

            i += 1
            if len_pid_list == len(pid_list):
                break
        pid_set = set(pid_list)
        print('一共%d页, 有%d个%s项目' % (i - 1, len(pid_set), category))
        return pid_set

    def check_new_projs(self):  # 获取新增project的项目编号，并更新上一周期预热中项目的状态
        # 检查新增的预热中项目
        pid_set1 = {x['_id'] for x in list(self.project.find({'状态': '预热中'}, projection={'_id': True}))}
        c_pids_1 = self.get_pid_list(category='预热中')
        new_projs = c_pids_1 - pid_set1
        print('新增%d个项目:' % len(new_projs), end=' ')
        for p_id in new_projs:  # 新增预热中项目
            try:  # 有些项目使用了上一周期已失败项目的id
                self.project.insert_one({'_id': p_id, '状态': '预热中', '项目动态信息': [], '各档动态信息': [],
                                         '状态变换时间0-1': self.now, '爬取次数': 0})
                print(p_id, end='  ')
            except Exception as e:
                print(e)
        print()

    def transfer_recodes(self):  # 转移未成功项目，可能与将来的project编号冲突
        failure_list = list(self.project.find({'状态': {'$in': ['众筹失败', '众筹未成功', '项目未成功']}}))
        for record in failure_list:
            self.failure_project.insert_one({'项目编号': record['_id'], '失败时间': self.now, '详细信息': record})
            self.project.delete_one({'_id': record['_id']})
            print('%s，转移数据！' % record['状态'], 'id: %s ' % record['_id'], '名称: %s ' % record['项目名称'])

    def start_craw(self):
        t = time.process_time()
        print('*********************************************************')
        print('开始更新', datetime.datetime.now())
        self.check_new_projs()  # 新增项目，并更新各项目的类别
        i = 1
        count_fail = 0  # 失败数
        # (1) 更新预热中项目信息
        p_dict1 = list(self.project.find({'状态': '预热中'}, projection={'_id': True, '爬取次数': True}))
        print('===================更新预热中的项目列表===================')
        a = 0  # 预热中项目个数
        a_b = 0  # 预热中->众筹中
        t1 = time.process_time()
        for proj in p_dict1:
            time.sleep(random.random())
            p_id, count_inqury = proj['_id'], proj['爬取次数']
            s_craw = Single_proj_craw(p_id=p_id, count_inqury=count_inqury)
            now_category = s_craw.category
            print(i, '  编号:', p_id, '第 %d 次监测!' % (count_inqury + 1))
            if count_inqury == 0:
                s_data = s_craw.start_craw()
                self.project.update_one({'_id': p_id},
                                        {'$set': s_data[0],
                                         '$push': {'项目动态信息': s_data[1]['项目动态信息'],
                                                   '各档动态信息': s_data[1]['各档动态信息']},
                                         '$inc': {'爬取次数': 1}},
                                        upsert=True)
                a += 1
            else:
                if now_category == '预热中':
                    s_data = s_craw.start_craw()
                    self.project.update_one({'_id': p_id}, {'$push': {'项目动态信息': s_data['项目动态信息'],
                                                                      '各档动态信息': s_data['各档动态信息']},
                                                            '$inc': {'爬取次数': 1}},
                                            upsert=True)
                    a += 1
                elif now_category == '众筹中':  # 更新为众筹中状态，记录状态变换时间
                    self.project.update_one({'_id': p_id}, {'$set': {'状态': now_category,
                                                                     '状态变换时间1-2': self.now}},
                                            upsert=True)
                    print('  转换为%s状态' % now_category)
                    a_b += 1
                else:
                    self.project.update_one({'_id': p_id},
                                            {'$set': {'状态': '众筹失败',
                                                      '状态变换时间1-2': self.now}},
                                            upsert=True)
                    print('众筹失败，不再监测！')
                    count_fail += 1
            i += 1
        print('共 %d 项, 用时 %.2f s' % (len(p_dict1), time.process_time() - t1))

        # (2) 更新众筹中项目信息
        p_dict2 = list(self.project.find({'状态': '众筹中'}, projection={'_id': True, '爬取次数': True}))
        print('===================更新众筹中的项目列表===================')
        b = 0  # 众筹中项目数量
        b_c = 0  # 众筹中->众筹成功
        t1 = time.process_time()
        for proj in p_dict2:
            time.sleep(random.random())
            t1 = time.process_time()
            try:
                p_id, count_inqury = proj['_id'], proj['爬取次数']
                s_craw = Single_proj_craw(p_id=p_id, count_inqury=count_inqury)
                now_category = s_craw.category
                print(i, '  编号:', p_id, '第 %d 次监测!' % (count_inqury + 1))
                if now_category == '众筹中':
                    s_data = s_craw.start_craw()
                    if datetime.datetime.now() < s_craw.end_time - datetime.timedelta(hours=12):
                        self.project.update_one({'_id': p_id}, {'$push': {'项目动态信息': s_data['项目动态信息'],
                                                                          '各档动态信息': s_data['各档动态信息']},
                                                                '$inc': {'爬取次数': 1}})
                    else:
                        self.project.update_one({'_id': p_id}, {'$set': {'评论': s_data[1]},
                                                                '$push': {'项目动态信息': s_data[0]['项目动态信息'],
                                                                          '各档动态信息': s_data[0]['各档动态信息']},
                                                                '$inc': {'爬取次数': 1}})
                    b += 1
                elif now_category == '众筹成功':  # 更新为众筹成功状态，记录状态变换时间
                    self.project.update_one({'_id': p_id}, {'$set': {'状态': now_category,
                                                                     '状态变换时间2-3': self.now}},
                                            upsert=True)
                    print('  转换为%s状态' % now_category)
                    b_c += 1
                else:
                    self.project.update_one({'_id': p_id},
                                            {'$set': {'状态': '众筹未成功',
                                                      '状态变换时间2-3': self.now}},
                                            upsert=True)
                    print('众筹未成功，不再监测！')
                    count_fail += 1
            except Exception as e:
                print('  爬取失败！', e)

            i += 1
        print('共 %d 项, 用时 %.2f s' % (len(p_dict2), time.process_time() - t1))

        # (3) 更新众筹成功项目信息
        p_dict3 = list(self.project.find({'状态': '众筹成功'}, projection={'_id': True, '爬取次数': True}))
        print('===================更新众筹成功的项目列表===================')
        c = 0  # 众筹成功项目数量
        c_d = 0  # 众筹成功->项目成功
        t1 = time.process_time()
        for proj in p_dict3:
            time.sleep(random.random())
            t1 = time.process_time()
            try:
                p_id, count_inqury = proj['_id'], proj['爬取次数']
                s_craw = Single_proj_craw(p_id=p_id, count_inqury=count_inqury)
                now_category = s_craw.category
                print(i, '  编号:', p_id, '第 %d 次监测!' % (count_inqury + 1))
                if now_category == '众筹成功':
                    s_data = s_craw.start_craw()
                    self.project.update_one({'_id': p_id}, {'$set': {'评论': s_data}, '$inc': {'爬取次数': 1}})
                    c += 1
                elif now_category == '项目成功':  # 更新为项目成功状态，记录状态变换时间
                    self.project.update_one({'_id': p_id}, {'$set': {'状态': now_category,
                                                                     '状态变换时间3-4': self.now}},
                                            upsert=True)
                    print('  转换为%s状态' % now_category)
                    c_d += 1
                else:
                    self.project.update_one({'_id': p_id}, {'$set': {'状态': '项目未成功',
                                                                     '状态变换时间3-4': self.now}},
                                            upsert=True)
                    print('项目未成功，不再监测！')
                    count_fail += 1
            except Exception as e:
                print('  爬取失败！', e)

            i += 1
        print('共 %d 项, 用时 %.2f s' % (len(p_dict3), time.process_time() - t1))
        print('=========================================================')
        print('本次更新结束', datetime.datetime.now())
        print('一共用时: %2.f s' % (time.process_time() - t))
        print('*********************************************************')

        return a, a_b, b, b_c, c, c_d, count_fail

# 发送电子邮件
def send_mail(title, content, mail_user, mail_pass, sender, receiver, mail_host='smtp.163.com'):
    message = MIMEText(content, 'plain')
    message['From'] = formataddr(['Ubuntu-京东众筹', sender])
    message['To'] = formataddr(['QQ', receiver])
    message['Subject'] = title
    try:
        smtpObj = smtplib.SMTP()
        smtpObj.connect(mail_host, 25)    # 25 为 SMTP 端口号
        smtpObj.login(mail_user, mail_pass)
        smtpObj.sendmail(sender, receiver, message.as_string())
        print("邮件发送成功!")
    except smtplib.SMTPException as e:
        print("Error: 无法发送邮件!")
        print('错误如下:', e)


if __name__ == '__main__':
    f = open('/home/yu/Desktop/1.txt')
    x = f.read()
    mail_user, mail_pass, sender, receiver = x.strip().split('/')

    try:
        # 爬取首页上的项目列表
        front_page = frontpage.Front_page()
        front_page.start_craw()

        # 爬取项目信息并处理数据
        c_craw = Collect_craw()
        c_craw.transfer_recodes()
        c_info = c_craw.start_craw()  # 爬取项目的详细信息
        c_craw.transfer_recodes()  # 转移已失败的众筹项目信息

        # 发送电子邮件
        t_time = datetime.datetime.now()
        t_time = t_time.strftime('%Y-%m-%d %H:%m:%S')
        title = '爬虫成功执行！'  # 邮件标题
        content = """时间: %s\n
预热中: %d 项\n预热中->众筹中: %d 项\n
众筹中: %d 项\n众筹中->众筹成功: %d 项\n
众筹成功: %d 项\n众筹成功->项目成功: %d 项\n
失败: %d项""" % (t_time, *c_info)  # 邮件正文
        print('小结:\n', content)
        send_mail(title, content, mail_user, mail_pass, sender, receiver)
    except Exception as e:
        title = '爬虫出现错误！'
        content = '时间: %s \n错误信息:\n %s' % (datetime.datetime.now(), e)
        print(e)
        send_mail(title, content,  mail_user, mail_pass, sender, receiver)
