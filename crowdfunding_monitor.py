#coding=utf-8
from pymongo import MongoClient
from urllib import request, parse
from bs4 import BeautifulSoup
from singlecrawl import Single_proj_craw
import frontpage
import socket
import datetime
import ssl
import re
import time
import random
import smtplib
import base64
from email.mime.text import MIMEText
from email.utils import formataddr

context = ssl._create_unverified_context()  # 不验证网页安全性
socket.setdefaulttimeout(15)  # 设置全局超时


class Collect_craw:

    def __init__(self):
        self.User_Agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:60.0) Gecko/20100101 Firefox/60.0'
        self.Host = 'z.jd.com'
        self.p_url = 'https://z.jd.com/bigger/search.html'
        self.p_getId = re.compile("\d+")
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

        pid_list = []
        i = 0
        while True:
            time.sleep(0.1)
            len_pid_list = len(pid_list)
            req = request.Request(self.p_url)
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
                    pid = self.p_getId.findall(url)[0]
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

    def update_orange(self, p_dict):  # 更新预热中项目
        count_fail = 0  # 失败数
        a = 0  # 预热中项目个数
        a_b = 0  # 预热中->众筹中
        for i, proj in enumerate(p_dict, start=1):
            time.sleep(random.random())
            p_id, count_inqury = proj['_id'], proj['爬取次数']
            try:
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
                elif now_category == '预热中':
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
                elif now_category == "重定向":
                    self.project.update_one({'_id': p_id},
                                            {'$set': {'状态': '众筹失败',
                                                      '状态变换时间1-2': self.now}},
                                            upsert=True)
                    print('众筹失败，不再监测！')
                    count_fail += 1
            except Exception as e:
                print('  爬取失败！', e)
            i += 1
        return a, a_b, count_fail

    def update_green(self, p_dict):  # 更新众筹中项目
        count_fail = 0
        b = 0  # 众筹中项目数量
        b_c = 0  # 众筹中->众筹成功
        for i, proj in enumerate(p_dict, start=1):
            time.sleep(random.random())
            try:
                p_id, count_inqury = proj['_id'], proj['爬取次数']
                s_craw = Single_proj_craw(p_id=p_id, count_inqury=count_inqury)
                now_category = s_craw.category
                print(i, '  编号:', p_id, '第 %d 次监测!' % (count_inqury + 1))
                if now_category == '众筹中':
                    s_data = s_craw.start_craw()
                    if datetime.datetime.now() < s_craw.end_time - datetime.timedelta(hours=24):
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
                elif now_category == "重定向":
                    self.project.update_one({'_id': p_id},
                                            {'$set': {'状态': '众筹未成功',
                                                      '状态变换时间2-3': self.now}},
                                            upsert=True)
                    print('众筹未成功，不再监测！')
                    count_fail += 1
            except Exception as e:
                print('  爬取失败！', e)
        return b, b_c, count_fail
        
    def update_zcsuc(self, p_dict):  # 更新众筹成功项目
        count_fail = 0
        c = 0  # 众筹成功项目数量
        c_d = 0  # 众筹成功->项目成功
        for i, proj in enumerate(p_dict, start=1):
            time.sleep(random.random())
            try:
                p_id, count_inqury = proj['_id'], proj['爬取次数']
                s_craw = Single_proj_craw(p_id=p_id, count_inqury=count_inqury)
                now_category = s_craw.category
                print(i, '  编号:', p_id, '第 %d 次监测!' % (count_inqury + 1))
                if now_category == '众筹成功':
                    #s_data = s_craw.start_craw()
                    #self.project.update_one({'_id': p_id}, {'$set': {'评论': s_data}, '$inc': {'爬取次数': 1}})
                    c += 1
                elif now_category == '项目成功':  # 更新为项目成功状态，记录状态变换时间，更新评论信息
                    s_data = s_craw.start_craw()
                    self.project.update_one({'_id': p_id}, {'$set': {'状态': now_category,
                                                                    '评论': s_data,
                                                                    '状态变换时间3-4': self.now}},
                                            upsert=True)
                    print('  转换为%s状态' % now_category)
                    c_d += 1
                elif now_category == "重定向":
                    self.project.update_one({'_id': p_id}, {'$set': {'状态': '项目未成功',
                                                                    '状态变换时间3-4': self.now}},
                                            upsert=True)
                    print('项目未成功，不再监测！')
                    count_fail += 1
            except Exception as e:
                print('  爬取失败！', e)
        return c, c_d, count_fail

    def start_craw(self):
        t = time.process_time()
        print('*********************************************************')
        print('开始更新', datetime.datetime.now())
        self.check_new_projs()  # 新增项目，并更新各项目的类别
        # (1) 更新预热中项目信息
        p_dict1 = list(self.project.find({'状态': '预热中'}, projection={'_id': True, '爬取次数': True}))
        print('===================更新预热中的项目列表===================')
        t1 = time.process_time()
        a, a_b, a_fail = self.update_orange(p_dict1)
        print('用时{:.2f}秒\n共{}项, 众筹失败{}项'.format(time.process_time() - t1, len(p_dict1), a_fail))

        # (2) 更新众筹中项目信息
        p_dict2 = list(self.project.find({'状态': '众筹中'}, projection={'_id': True, '爬取次数': True}))
        print('===================更新众筹中的项目列表===================')
        t1 = time.process_time()
        b, b_c, b_fail = self.update_green(p_dict2)
        print('用时{:.2f}秒\n共{}项, 众筹失败{}项'.format(time.process_time() - t1, len(p_dict2), b_fail))

        # (3) 更新众筹成功项目信息
        p_dict3 = list(self.project.find({'状态': '众筹成功'}, projection={'_id': True, '爬取次数': True}))
        t1 = time.process_time()
        print('===================更新众筹成功的项目列表===================')
        c, c_d, c_fail = self.update_zcsuc(p_dict3)
        print('用时{:.2f}秒\n共{}项, 众筹失败{}项'.format(time.process_time() - t1, len(p_dict3), c_fail))

        # 更新总况
        print('=========================================================')
        print('本次更新结束', datetime.datetime.now())
        print('一共用时: %2.f s' % (time.process_time() - t))
        print('*********************************************************')

        return a, a_b, b, b_c, c, c_d, a_fail+b_fail+c_fail

# 发送电子邮件
def send_mail(title, content, mail_user, mail_pass, sender, receiver, mail_host='smtp.163.com'):
    message = MIMEText(content, 'plain')
    message['From'] = formataddr(['Ubuntu-京东众筹', sender])
    message['To'] = formataddr(['QQ', receiver])
    message['Subject'] = title
    try:
        smtpObj = smtplib.SMTP_SSL(mail_host, 465)
        smtpObj.ehlo()
        #smtpObj.connect(mail_host, 465)    # 465 为 SMTP SSL加密 端口号
        smtpObj.login(mail_user, mail_pass)
        smtpObj.sendmail(sender, receiver, message.as_string())
        smtpObj.close()
        return "Success!"
    except smtplib.SMTPException as e:
        print("Error: 无法发送邮件!")
        print('错误如下:', e)
        smtpObj.close()
        return "Failure!"


if __name__ == '__main__':
    print("开始时间", format(datetime.datetime.now()))
    f = open('mail_username.txt')
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
