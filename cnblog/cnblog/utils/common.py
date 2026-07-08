from datetime import datetime
import pytz  # 或使用 zoneinfo（Python 3.9+）
import httpx
import tldextract
import json
import random
from pathlib import Path
from urllib.parse import urlparse

from lxml import html

# 取url子域名  www
async def get_submain(url):
    parse = urlparse(url)
    subdomain = parse.netloc.split(".")[0]
    return {"scheme":parse.scheme,"subdomain":subdomain,"domain":f'{parse.scheme}://{parse.netloc}',"netloc":parse.netloc,"path":parse.path}

# 时间字符串 转 时间对象
async def str_datetime(str):
    try:
        # 1. 先解析为 datetime 对象（无时区）
        dt_naive = datetime.strptime(str, '%Y-%m-%d %H:%M')
        # 2. 添加时区（例如假设为北京时间 UTC+8）
        tz = pytz.timezone('Asia/Shanghai')
        dt_aware = tz.localize(dt_naive)   # 或使用 dt_aware = dt_naive.replace(tzinfo=...)

        return dt_aware
    except ValueError:
        pass

# article 作者信息
async def article_author(url):
    resp = None
    url = f"{url}/ajax/news"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)

    ele = html.fromstring(html=resp.text)
    nickname_list = ele.xpath('//div[@id="profile_block"]/a[1]/text()')
    nickname = nickname_list[0].strip() if nickname_list else None
    return nickname

# article 其他信息
async def article_info(url:str):
    extract_res = tldextract.extract(url)
    subdomain = extract_res.subdomain
    resp = None
    async with httpx.AsyncClient() as client:
        if subdomain == "www":
            url_split = url.split("/")
            postId = int(url_split[5])
            urlName = url_split[3]
            request_url = f"https://www.cnblogs.com/{urlName}/ajax/post-accessories?postId={postId}"
            resp = await client.get(request_url)
            
        else:
            # subdomain == "news"
            url_split = url.split("/")
            contentId = url_split[4]
            request_url = f"https://news.cnblogs.com/NewsAjax/GetAjaxNewsInfo?contentId={contentId}"
            resp = await client.get(request_url)
    resp = json.loads(resp.text)
    if "TotalView" in resp:
        views = resp["TotalView"]
    else:
        views = resp["postStats"]["viewCount"]
    return views

# 解析cookie字符串为字典格式
def parse_cookie_string(cookie_str):
    cookie_dict = {}
    for item in cookie_str.strip().split('; '):
        if '=' not in item:
            continue
        key, value = item.split('=', 1)
        cookie_dict[key.strip()] = value.strip()
    return cookie_dict

# 从文件中读取cookie字符串
def get_random_cookie():
    root_path = Path(__file__).parent.parent.parent
    cookie_path = root_path / 'scripts/cookies.js'
    cookies = None
    with open(cookie_path,"r",encoding="utf-8") as f:
        cookies = json.load(f)
    cookie_str = random.choice(cookies)
    return parse_cookie_string(cookie_str)
