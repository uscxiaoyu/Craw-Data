from urllib import request, parse
from bs4 import BeautifulSoup
from pymongo import MongoClient
import datetime
import ssl
import re
import time
import json
import random

ssl._create_default_https_context = ssl._create_unverified_context  # 全局取消网页安全验证


