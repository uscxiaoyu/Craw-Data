from urllib import request, parse
from bs4 import BeautifulSoup
from pymongo import MongoClient
import datetime
import ssl
import re
import time
import json
import random
context = ssl._create_unverified_context()  # 不验证网页安全性


class Single_proj_craw:

    def __init__(self, p_id, category, end_time):
        self.User_Agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:59.0) Gecko/20100101 Firefox/59.0'
        self.Host = 'z.jd.com'
        self.p_id = p_id
        self.category = category  # 预热中、众筹中、众筹成功、项目成功
        self.end_time = end_time  # 众筹结束时间

    def page_source(self):
        url_1 = 'http://z.jd.com/project/details/%s.html' % self.p_id
        req = request.Request(url_1)
        req.add_header('User-Agent', self.User_Agent)
        req.add_header('Host', self.Host)
        with request.urlopen(req, context=context) as f:
            rawhtml = f.read().decode('utf-8')
            self.h_soup = BeautifulSoup(rawhtml, 'html.parser')

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
        # (1)项目信息
        div1 = self.h_soup.find_all('div', {'class': 'project-introduce'})[0]
        proj_name = div1.find_all('h1', {'class': 'p-title'})[0].string  # 项目名称

        div1_2 = div1.find_all('p', {'class': "p-target"})[0]
        p_d = re.compile('\d+')
        end_time = div1_2.find_all('span', {'class': 'f_red'})[0].string.strip()  # 提取截止日期
        end_time = '-'.join(p_d.findall(end_time))
        end_time = datetime.datetime.strptime(end_time, '%Y-%m-%d')  # 截止日期
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
                key = li.find_all('div', {'class': "key"})[0].string
                val = li.find_all('div', {'class': "val"})[0].string
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
            indiv_info[str(i)] = {'sup_price': sup_price,
                                  'lim_num': lim_num,
                                  'redound_info': redound_info,
                                  'deliver_info': deliver_info}

        return {'proj_name': proj_name, 'target_fund': target_fund, 'end_time': end_time,
                'sort_name': sort_name, 'promoter_href': prom_href, 'promoter_name': prom_name,
                'company_name': company_name, 'company_address': company_address, 'company_hours': company_hours,
                'company_phone': company_phone, 'ind_info': indiv_info}

    def update_data(self):
        # 当前筹集金额、当前进度、当前支持人数
        div1 = self.h_soup.find_all('div', {'class': 'project-introduce'})[0]
        now_fund = div1.find_all('p', {'class': "p-num"})[0].get_text()[1:]  # 当前项目筹集金额
        now_percent, now_supporters = None, None
        try:
            div1_1 = div1.find_all('p', {'class': "p-progress"})[0]
            now_percent = div1_1.find_all('span', {'class': "fl percent"})[0].string[4:-1]  # 当前进度
            now_supporters = div1_1.find_all('span', {'class': "fr"})[0].string[:-4]  # 当前支持人数
        except IndexError:
            print('No progress')

        # 各档支持信息
        div4 = self.h_soup.find_all('div', {'class': "box-grade "})
        indiv_info = {}
        for i, d in enumerate(div4):
            now_num_sup = d.find_all('div', {'class': "t-people"})[0].span.string.strip()  # 当前支持人数
            indiv_info[str(i)] = {'now_num_sup': now_num_sup}

        # 当前点赞人数、当前关注者数、项目创建时间、项目更新时间
        p_praise = re.compile('"praise":(\d+)')
        p_focus = re.compile('"focus":(\d+)')
        p_createTime = re.compile('"createTime":"(\d+-\d+-\d+ \d+:\d+:\d+)"')
        p_updateTime = re.compile('"updateTime":"(\d+-\d+-\d+ \d+:\d+:\d+)"')

        praise = p_praise.findall(self.j_soup)[0]  # 点赞人数
        focus = p_focus.findall(self.j_soup)[0]  # 关注人数
        createTime = p_createTime.findall(self.j_soup)[0]
        createTime = datetime.datetime.strptime(createTime, "%Y-%m-%d %H:%M:%S") # 项目创建时间

        updateTime = p_updateTime.findall(self.j_soup)[0]  # 项目更新时间
        updateTime = datetime.datetime.strptime(updateTime, "%Y-%m-%d %H:%M:%S") # 项目创建时间

        return {'dyn_prj_info': {'now_fund': now_fund, 'now_percent': now_percent, 'now_supporters': now_supporters,
                    'now_praise': praise, 'now_foucus': focus, 'createTime': createTime, 'updateTime': updateTime},
                'dyn_ind_info': indiv_info}

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
                reviews[str(record['topicId'])] = {'createTime': record['createTime'], 'likecount': record['likecount'],
                                                   'replys': record['replys'], 'topicContent': record['topicContent']}

            if totalPage > i:
                i += 1
            else:
                break

        return {'num_page': totalPage, 'num_records': totalRecord, 'reviews': reviews}

    def start_craw(self):
        self.page_source()  # 网页静态信息
        if self.category == '预热中':
            return self.basic_data(), self.update_data()

        elif self.category == '众筹中':
            if datetime.datetime.now() < self.end_time - datetime.timedelta(hours=12):
                return self.update_data()
            else:
                return self.update_data(), self.review_data()

        elif self.category == '众筹成功':
            return self.review_data()


class Collect_craw:

    def __init__(self, e_page=40):
        self.User_Agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:59.0) Gecko/20100101 Firefox/59.0'
        self.Host = 'z.jd.com'
        self.e_page = e_page
        # 连接MongoDB数据库
        client = MongoClient('localhost', 27017)
        db = client.moniter_cloudfunding
        self.project = db.projects
        # 如果是第一次启动，则以下集合为空集
        self.pid_set1 = {x['_id'] for x in list(self.project.find({'category': '预热中'}, projection={'_id': True}))}
        self.pid_set2 = {x['_id'] for x in list(self.project.find({'category': '众筹中'}, projection={'_id': True}))}
        self.pid_set3 = {x['_id'] for x in list(self.project.find({'category': '众筹成功'}, projection={'_id': True}))}
        self.pid_set4 = {x['_id'] for x in list(self.project.find({'category': '项目成功'}, projection={'_id': True}))}

    def get_pid_list(self, category):  # 获取制定范围页面的项目id
        '''
        :param pages: 页数
        :return: 项目id列表
        '''
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
        i = 1
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
            if i == self.e_page or len_pid_list == len(pid_list):
                print('一共%d页, 有%d个%s项目' % (i - 2, len_pid_list, category))
                break

        return set(pid_list)

    def update_pid_cats(self):  # 获取新增project的项目编号
        # 当前各类别页面下的项目列表
        c_pids_1 = self.get_pid_list(category='预热中')
        c_pids_2 = self.get_pid_list(category='众筹中', )
        c_pids_3 = self.get_pid_list(category='众筹成功')
        c_pids_4 = self.get_pid_list(category='项目成功')

        for p_id in c_pids_1 - self.pid_set1:  # 新增项目
            self.project.insert_one({'_id': p_id, 'category': '预热中', 'state': 'first',
                                     'dyn_prj_info': [], 'dyn_ind_info': []})

        for p_id in c_pids_2 - self.pid_set2:  # 新增众筹中项目
            self.project.update_one({'_id': p_id}, {'$set': {'category': '众筹中'}})

        for p_id in c_pids_3 - self.pid_set3:  # 新增众筹成功项目
            self.project.update_one({'_id': p_id}, {'$set': {'category': '众筹成功'}})

        for p_id in (self.pid_set2 - c_pids_2) - (c_pids_3 - self.pid_set3):  # 众筹未成功项目
            self.project.update_one({'_id': p_id}, {'$set': {'category': '众筹未成功'}})

        for p_id in c_pids_4 - self.pid_set4:  # 新增项目成功项目
            self.project.update_one({'_id': p_id}, {'$set': {'category': '项目成功'}})

        for p_id in (self.pid_set3 - c_pids_3) - (c_pids_4 - self.pid_set4):  # 项目未成功项目
            self.project.update_one({'_id': p_id}, {'$set': {'category': '项目未成功'}})


    def start_craw(self):
        print('开始更新', datetime.datetime.now())
        self.update_pid_cats()  # 新增项目，并更新各项目的类别
        i = 1

        # x对应项目静态信息，y对应项目动态信息和各档支持动态信息，z对应评论信息
        p_dict1 = list(self.project.find({'category': '预热中'}, projection={'_id': True, 'state': True}))
        print('更新预热中的项目列表：')
        for proj in p_dict1:
            time.sleep(random.random())
            t1 = time.clock()
            p_id, category, end_time = proj['_id'], '预热中', proj['end_time']
            s_craw = Single_proj_craw(p_id=p_id, category=category, end_time=end_time)
            x, y = s_craw.start_craw()
            self.project.update_one({'_id': p_id},
                                    {'$set': x,
                                     '$push': {'dyn_prj_info': y['dyn_prj_info'], 'dyn_ind_info': y['dyn_ind_info']}},
                                    upsert=True)

            print(i, '项目编号: %s' % p_id, '用时: %.2f s' % (time.clock() - t1))
            i += 1

        p_dict2 = list(self.project.find({'category': '众筹中'}, projection={'_id': True, 'end_time': True}))
        print('更新众筹中的项目列表：')
        for proj in p_dict2:
            time.sleep(random.random())
            t1 = time.clock()
            p_id, category, end_time = proj['_id'], '众筹中', proj['end_time']
            s_craw = Single_proj_craw(p_id=p_id, category=category, end_time=end_time)
            if datetime.datetime.now() < end_time - datetime.timedelta(hours=12):
                y = s_craw.start_craw()
                self.project.update_one({'_id': p_id}, {'$push': {'dyn_prj_info': y['dyn_prj_info'],
                                                                  'dyn_ind_info': y['dyn_ind_info']}})
            else:
                y, z = s_craw.start_craw()
                self.project.update_one({'_id': p_id}, {'$set': z,
                                                        '$push': {'dyn_prj_info': y['dyn_prj_info'],
                                                                  'dyn_ind_info': y['dyn_ind_info']}})

            print(i, '项目编号: %s' % p_id, '用时: %.2f s' % (time.clock() - t1))
            i += 1

        p_dict3 = list(self.project.find({'category': '众筹成功'}, projection={'_id': True, 'end_time': True}))
        print('更新众筹成功的项目列表：')
        for proj in p_dict3:
            time.sleep(random.random())
            t1 = time.clock()
            p_id, category, end_time = proj['_id'], '众筹成功', proj['end_time']
            s_craw = Single_proj_craw(p_id=p_id, category=category, end_time=end_time)
            z = s_craw.start_craw()
            self.project.update_one({'_id': p_id}, {'$set': z})
            print(i, '项目编号: %s' % p_id, '用时: %.2f s' % (time.clock() - t1))
            i += 1

        print('更新结束', datetime.datetime.now())


if __name__ == '__main__':
    c_craw = Collect_craw()
    #c_craw.start_craw()
