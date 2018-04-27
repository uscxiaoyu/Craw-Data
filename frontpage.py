from urllib import request
from bs4 import BeautifulSoup
from pymongo import MongoClient
import datetime
import ssl
import re
import json

ssl._create_default_https_context = ssl._create_unverified_context  # 全局取消网页安全验证

class Front_page:

    def __init__(self):
        client = MongoClient('localhost', 27017)
        db = client.moniter_cloudfunding
        self.project = db.front_page
        self.pattern = re.compile("\d+")

        url1 = 'https://z.jd.com/sceneIndex.html?from=header'
        user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:59.0) Gecko/20100101 Firefox/59.0'
        host = 'z.jd.com'
        req1 = request.Request(url1)
        req1.add_header('User-Agent', user_agent)
        req1.add_header('Host', host)
        f1 = request.urlopen(req1)
        x1 = f1.read().decode()
        self.soup = BeautifulSoup(x1, 'lxml')

        url2 = 'https://z.jd.com/getPreheatList.action'
        req2 = request.Request(url2)
        req2.add_header('User-Agent', user_agent)
        req2.add_header('Host', host)
        req2.add_header('Referer', 'https://z.jd.com/sceneIndex.html?from=header')
        f2 = request.urlopen(req2)
        x2 = f2.read().decode()
        self.json_x = json.loads(x2)

    def find_broadcast(self, div):
        urls = [x.a['href'] for x in div.find_all('li')]
        return [self.pattern.findall(x)[0] for x in urls]

    def pick_pid(self, div):
        info_top = div.find_all('div', {'class': 'infor-top clearfix'})
        s_topic = div.find_all('a', {'class': "item-a"})

        top_urls = [x.a['href'] for x in info_top]
        top_ids = [self.pattern.findall(x)[0] for x in top_urls]  # 左上大图项目id

        spe_urls = [x['href'] for x in s_topic]
        spe_ids = [self.pattern.findall(x)[0] for x in spe_urls]  # 其它图项目id

        return {'左上大图': top_ids, '其它图': spe_ids}

    def broadcastproj(self):  # (1) 获取broadcast轮播的项目列表
        class_type = ['left', 'r-t', 'r-b-l', 'r-b-r']  # 左、右上、右下左、右下右
        broadcast_dict = {}
        for c in class_type:
            b_div = self.soup.find_all('div', {'class':c})[0]
            broadcast_dict[c] = self.find_broadcast(b_div)
        return {'轮播': broadcast_dict}

    def hotproj(self):  # (2) 获取热门推荐项目列表
        div_hot = self.soup.find('div', {'class': 'hot-push-box'})
        urls = [x.a['href'] for x in div_hot.ul.find_all('li')]
        return {"热门推荐": [self.pattern.findall(x)[0] for x in urls]}

    def newproj(self): # (3) 获取最近上架项目列表
        div_new = self.soup.find('div', {'class': 'new-list'})
        urls = [x.a['href'] for x in div_new.ul.find_all('li')]
        return {"最新上架": [self.pattern.findall(x)[0] for x in urls]}

    def nearendproj(self):  # (4) 即将结束项目列表
        div_end = self.soup.find_all('div', {'class': 'new-list'})[1]
        urls = [x.a['href'] for x in div_end.ul.find_all('li')]
        return {"即将结束": [self.pattern.findall(x)[0] for x in urls]}

    def demosproj(self):  # (5) 各类展品
        div_sum = self.soup.find_all('div', {'class': 'tab-div'})
        demo_dict = {}
        d_name = ['新奇酷玩', '健康出行', '生活美学', '美食市集', '文化艺术', '惠民扶贫']
        for i, d in enumerate(d_name):
            div_d = div_sum[i]
            demo_dict[d] = self.pick_pid(div_d)
        return {"demostr_proj": demo_dict}

    def preheatproj(self):  # (6) 即将上架
        return {"即将上架": [x['itemId'] for x in self.json_x]}

    def start_craw(self):
        broadcast_data = self.broadcastproj()
        hot_data = self.hotproj()
        new_data = self.newproj()
        nearend_data = self.nearendproj()
        demo_data = self.demosproj()
        preheat_data = self.preheatproj()
        self.project.insert_one({'监测时间': datetime.datetime.now(),
            **broadcast_data, **hot_data, **new_data, **nearend_data, **demo_data, **preheat_data})


if __name__ == '__main__':
    front_page = Front_page()
