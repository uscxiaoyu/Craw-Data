from urllib import request, parse
from bs4 import BeautifulSoup, Comment
from pymongo import MongoClient
import ssl
import re
import time
import json
context = ssl._create_unverified_context()


class Craw:

    def __init__(self):
        self.User_Agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:59.0) Gecko/20100101 Firefox/59.0'
        self.Host = 'z.jd.com'
        self.b_page = 1  # 开始页面
        self.e_page = 12  # 终止页面
        self.category = '项目成功'  # 预热中、众筹中、众筹成功、项目成功

    def get_pid_list(self):  # 获取制定范围页面的项目id
        '''
        :param pages: 页数
        :return: 项目id列表
        '''
        if self.category == '预热中':
            status, class_info, sort = '1', 'info type_future', 'jjks'
        elif self.category == '众筹中':
            status, class_info, sort = '2', 'info type_now', 'zhtj'
        elif self.category == '众筹成功':
            status, class_info, sort = '4', 'info type_succeed', 'zhtj'
        elif self.category == '项目成功':
            status, class_info, sort = '8', 'info type_xm', 'zhtj'

        p_url = 'https://z.jd.com/bigger/search.html'
        pattern = re.compile("\d+")
        pid_list = []
        for i in range(self.b_page, self.e_page + 1):
            time.sleep(0.1)
            req = request.Request(p_url)
            # status: 预热中 '1', 众筹中 '2', 众筹成功 '4' 项目成功 '8'
            post_list = [('categoryId', ''), ('keyword', ''), ('page', '%d' % i), ('parentCategoryId', ''),
                         ('productEnd', ''), ('sceneEnd', ''), ('sort', sort), ('status', status)]
            post_data = parse.urlencode(post_list)
            req.add_header('User-Agent', self.User_Agent)
            req.add_header('Referer', 'https://z.jd.com/bigger/search.html')
            req.add_header('Host', self.Host)

            with request.urlopen(req, data=post_data.encode('utf-8'), context=context) as f:
                web_data = f.read()
                soup = BeautifulSoup(web_data, 'html.parser')
                ul = soup.find_all('div', {'class': 'l-result'})[0].ul  # 注意，不同状态的class有区别
                # info type_xm项目成功, info type_succeed众筹成功, info type_now众筹中, info type_future 预热中
                li = ul.find_all('li', {'class': class_info})
                for l in li:
                    url = l.find_all('a')[0].get('href')
                    matcher = re.search(pattern, url)
                    pid_list.append(matcher.group(0))

        return pid_list

    def get_static(self, p_id):  # 静态数据
        '''
        :param p_id: 项目编号
        :return:
        '''
        url = 'http://z.jd.com/project/details/%s.html' % p_id
        req = request.Request(url)
        req.add_header('User-Agent', self.User_Agent)
        req.add_header('Host', self.Host)
        with request.urlopen(req, context=context) as f:
            rawhtml = f.read().decode('utf-8')
            soup = BeautifulSoup(rawhtml, 'html.parser')

            # (1)项目信息
            div1 = soup.find_all('div', {'class': 'project-introduce'})[0]
            proj_name = div1.find_all('h1', {'class': 'p-title'})[0].string  # 项目名称
            comments = div1.find_all(text=lambda text: isinstance(text, Comment))
            state = comments[0].strip()  # 项目状态
            now_fund = div1.find_all('p', {'class': "p-num"})[0].get_text()[1:]  # 当前项目筹集金额
            now_percent, now_supporters = None, None
            try:
                div1_1 = div1.find_all('p', {'class': "p-progress"})[0]
                now_percent = div1_1.find_all('span', {'class': "fl percent"})[0].string[4:-1]  # 当前进度
                now_supporters = div1_1.find_all('span', {'class': "fr"})[0].string[:-4]  # 当前支持人数
            except IndexError:
                print('No progress')

            div1_2 = div1.find_all('p', {'class': "p-target"})[0]
            end_time = div1_2.find_all('span', {'class': 'f_red'})[0].string.strip()  # 截止日期
            target_fund = div1_2.find_all('span', {'class': 'f_red'})[1].get_text()[1:]  # 目标金额


            s = soup.find_all('div', {'class': "tab-share-l"})
            sort_name = s[0].a['data-attr']  # 项目所属类别

            # (2)发起人信息
            div2 = soup.find_all('div', {'class': "promoters-name"})[0]
            prom_href = div2.find_all('a')[0]['href']  # 发起人href
            prom_name = div2.find_all('a')[0]['title']  # 发起人名称

            # (3)公司信息
            company_name, company_address, company_phone, company_hours = None, None, None, None  # 先设为None
            try:
                div3 = soup.find_all('ul', {'class': "contact-box"})[0]
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
            div4 = soup.find_all('div', {'class': "box-grade "})
            indiv_info = {}
            for i, d in enumerate(div4):
                sup_price = d.find_all('div', {'class': "t-price"})[0].span.string.strip()  # 支持价位
                now_num_sup = d.find_all('div', {'class': "t-people"})[0].span.string.strip()  # 当前支持人数
                d_1 = d.find_all('div', {'class': "box-content"})
                lim_num = d_1[0].find_all('span', {'class': "limit-num"})[0].string  # 限制人数
                redound_info = d_1[0].find_all('p', {'class': "box-intro"})[0].string.strip()  # 回报内容
                deliver_info = d_1[0].find_all('p', {'class': "box-item"})[1].get_text()  # 发货时间
                indiv_info[str(i)] = {'sup_price': sup_price,
                                      'now_num_sup': now_num_sup,
                                      'lim_num': lim_num,
                                      'redound_info': redound_info,
                                      'deliver_info': deliver_info}

        return {'_id': p_id, 'proj_name': proj_name, 'target_fund': target_fund, 'end_time': end_time,
                'sort_name': sort_name, 'prom_href': prom_href, 'prom_name': prom_name, 'sate': state,
                'company_name': company_name, 'company_address': company_address, 'company_hours': company_hours,
                'now_fund': now_fund, 'now_percent': now_percent, 'now_supporters': now_supporters,
                'indiv_info': indiv_info}

    def get_json(self, p_id):  # 动态数据
        '''
        :return:
        '''
        url = 'http://sq.jr.jd.com/cm/getCount?'
        req = request.Request(url)
        req.add_header('User-Agent', self.User_Agent)
        req.add_header('Referer', 'http://z.jd.com/project/details/%s.html' % p_id)
        req.add_header('Host', self.Host)

        post_list = [('_', '15242091922'),
                     ('callback', 'jQuery183000564758012421237_1524209188840'),
                     ('key', '1000'),
                     ('pin', ''),
                     ('systemId', p_id),
                     ('temp', '0.29549820811900180')]  # 关键在于systemID，即项目编号

        post_data = parse.urlencode(post_list)

        with request.urlopen(req, data=post_data.encode('utf-8')) as f:
            x = f.read().decode()
            p_praise = re.compile('"praise":(\d+)')
            p_focus = re.compile('"focus":(\d+)')
            p_createTime = re.compile('"createTime":"(\d+-\d+-\d+ \d+:\d+:\d+)"')
            p_updateTime = re.compile('"updateTime":"(\d+-\d+-\d+ \d+:\d+:\d+)"')

            praise = p_praise.findall(x)[0]  # 点赞人数
            focus = p_focus.findall(x)[0]  # 关注人数
            createTime = p_createTime.findall(x)[0]  # 项目创建时间
            updateTime = p_updateTime.findall(x)[0]  # 项目更新时间

        return {'_id': p_id, 'now_praise': praise, 'now_foucus': focus,
                'createTime': createTime, 'updateTime': updateTime}

    def update_data(self):

        return

    def get_review(self, p_id):
        url = 'https://sq.jr.jd.com/topic/getTopicList?'
        req = request.Request(url)
        req.add_header('User-Agent', self.User_Agent)
        req.add_header('Referer', 'http://z.jd.com/project/details/%s.html' % p_id)
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
                         ('systemId', '%s' % p_id),
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

        return {'p_id': p_id, 'totalPage': totalPage, 'totalRecord': totalRecord, 'reviews': reviews}

    def start_craw(self):
        p_ids = self.get_pid_list()
        for i, p_id in enumerate(p_ids):
            time.sleep(0.3)
            print('睡眠0.3s')
            t1 = time.clock()
            static_cont = self.get_static(p_id)  # 网页静态信息
            dynamic_cont = self.get_json(p_id)  # 动态信息
            review_cont = self.get_review(p_id)  # 评论信息
            merge = {**static_cont, **dynamic_cont, **review_cont}
            project.insert_one(merge)
            print(i, '项目编号: %s' % p_id, '用时: %.2f s' % (time.clock() - t1))


if __name__ == '__main__':
    client = MongoClient('localhost', 27017)
    db = client.succ_cloudfunding
    project = db.projects
    craw = Craw()
    craw.category = '预热中'
    #craw.start_craw()