from urllib import request, parse
from bs4 import BeautifulSoup
from pymongo import MongoClient
from bson import ObjectId
import datetime
import ssl
import re
import time
import json
import random

ssl._create_default_https_context = ssl._create_unverified_context  # 全局取消网页安全验证

client = MongoClient('localhost', 27017)
db = client.moniter_crowdfunding
project = db.projects
f_project = db.failure_projects
p_founder = db.founders  # 新建founders集合, 用于存储项目信息
User_Agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:60.0) Gecko/20100101 Firefox/60.0'
Host = 'z.jd.com'

def crawData(href, _id):
    post_data = parse.urlencode({"flag":"2", "id":_id})
    req = request.Request(href)
    req.add_header('User-Agent', User_Agent)
    req.add_header('Referer', f'http://z.jd.com/funderCenter.action?{post_data}')
    req.add_header('Host', Host)
    with request.urlopen(req, data=post_data.encode('utf-8')) as f:
        raw_html = f.read().decode()
        
    return raw_html

def soupData(raw):
    h_soup = BeautifulSoup(raw, 'html.parser')
    cat_div = h_soup.find('div', {'class': 'tab_cont db'})
    p_d = re.compile('(\d+)')
    
    c_dict = {}
    if cat_div:
        for x in cat_div.findAll('li'):
            prj_href = str(x).split("'")[1]
            prj_id = p_d.findall(prj_href)[0]
            c_dict[prj_id] = {'prj_name': x.p.string, 'prj_desc': x.a.string, 'prj_href': prj_href}
        
    return c_dict

def checkOtherCols():
    suc_ids = list(set(x['_id'] for x in project.find({}, projection={'_id':1})))  # 除失败项目之外的所有项目信息
    for p_id in suc_ids[::-1]:  # 有部分文档以ObjectId作为_id
        if isinstance(p_id, ObjectId):
            print(f"success {p_id}")
            t_id = project.find_one({"_id":p_id}, projection={'项目编号':1})
            suc_ids.remove(p_id)
            suc_ids.append(t_id['项目编号'])
    
    fail_ids = list(set(x['详细信息']['_id'] for x in f_project.find({}, projection={'详细信息._id':1})))
    for p_id in fail_ids[::-1]:  # 将_id为ObjectID类型的替换为项目编号
        if isinstance(p_id, ObjectId):
            print(f"failure {p_id}")
            t_id = f_project.find_one({"详细信息._id":p_id}, projection={"详细信息.项目编号":1})
            fail_ids.remove(p_id)
            fail_ids.append(t_id["详细信息"]["项目编号"])
            
    return set(suc_ids) | set(fail_ids)

def insert_data(p_id):
    item = {'_id': p_id}
    try:
        for key in hrefs:
            raw = crawData(hrefs[key], item['_id'])
            c_dict = soupData(raw)
            item[key] = c_dict
        p_founder.insert_one(item)
        return 1
    except Exception as e:
        print(f"{p_id}插入失败!错误提示:{e}")
        return 0

def insert_dataset(p_ids):
    inserted, notInserted = [], []
    for p_id in p_ids:
        if insert_data(p_id):
            inserted.append(p_id)
        else:
            notInserted.append(p_id)
            
    return inserted, notInserted

def get_newIDs(p_founder=p_founder):
    now_ids = []
    new_res = []
    for x in p_founder.find({}):
        temp = list(x['支持项目'].keys()) + list(x['关注项目'].keys()) + list(x['发起项目'].keys())
        now_ids.append(x['_id'])
        new_res.extend(temp)
        
    return set(new_res) - set(now_ids)


if __name__ == "__main__":
    ids = checkOtherCols()
    hrefs = {'支持项目': 'http://z.jd.com/f/my_support.action?',
            '关注项目': 'http://z.jd.com/f/my_focus.action?', 
            '发起项目': 'http://z.jd.com/f/my_project.action?'}
    j = 1
    while True:
        time.sleep(10)
        print(f"第{j}轮")
        newIDs = get_newIDs()
        if newIDs:
            inserted, notinserted = insert_dataset(newIDs)
            j += 1
        else:
            break
