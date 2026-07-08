import httpx

import asyncio

from lxml import html

import tldextract
import json

from urllib.parse import urlparse

url = "https://www.cnblogs.com/xuri"

async def test(url):
    resp = None
    url = f"{url}/ajax/news"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)

    ele = html.fromstring(html=resp.text)
    fans = ele.xpath('//a[contains(@class, "follower-count")]/text()')
    if fans:
        fans_text = fans[0].strip()
    else:
        fans_text = None

    nickname = ele.xpath('//div[@id="profile_block"]/a[1]/text()')
    if nickname:
        nickname_text = nickname[0].strip()
    else:
        nickname_text = None
    return fans_text,nickname_text

# url ="https://www.cnblogs.com/test-gang/p/21248554"
url = "https://www.cnblogs.com/xuri/p/21224292/excelize_v2_11_0"

# url = "https://news.cnblogs.com/n/830229/"
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
    print(views)

url = "https://www.cnblogs.com/lingyanspace"
async def test_http(url):
    resp = None
    url = f"{url}/ajax/news"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)

    ele = html.fromstring(html=resp.text)
    nickname_list = ele.xpath('//div[@id="profile_block"]/a[1]/text()')
    nickname = nickname_list[0].strip("") if nickname_list else None
    print("nickname::::",nickname)

asyncio.run(test_http(url))


from urllib.parse import urlparse

# url = "https://news.cnblogs.com/n/page/2"
url = "https://www.cnblogs.com/xingce/p/21172839"
url = "https://www.cnblogs.com/chaogex/p/21240096"
url = "https://www.cnblogs.com/xuri/p/21224292/excelize_v2_11_0"
def test_url(url):
    parse = urlparse(url)
    print(parse)
    subdomain = parse.netloc.split(".")[0]
    return {"scheme":parse.scheme,"subdomain":subdomain,"domain":f'{parse.scheme}://{parse.netloc}',"netloc":parse.netloc,"path":parse.path}

parse_url = test_url(url)

print(parse_url["path"].split("/"))



