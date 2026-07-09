import scrapy
from cnblog.items import ArticleItem

from cnblog.utils.common import article_author,str_datetime,article_info,get_submain,get_random_cookie


class ArticleSpider(scrapy.Spider):
    name = "article"
    allowed_domains = ["www.cnblogs.com","news.cnblogs.com"]
    
    start_urls = [
        "https://news.cnblogs.com/",
        "https://www.cnblogs.com/",
    ]

    cookie = get_random_cookie()

    async def parse(self, response):
        url = response.url
        self.logger.info(f"🚀🚀🚀🚀🚀parse:🚀🚀🚀🚀🚀 :  {url}")
        parse_url = await get_submain(url)
        submain = parse_url["subdomain"]

        next_url = None
        # 获取首页文章列表
        if submain == "www":
            article_list = response.xpath('//article[@class="post-item"]')
            for art in article_list:
                item = ArticleItem()
                item['url'] = art.xpath('.//a[@class="post-item-title"]/@href').get()
                item['title'] = art.xpath('.//a[@class="post-item-title"]/text()').get()
                item['description'] = art.xpath('.//p[@class="post-item-summary"]/text()[last()]').get()
                item['cover_image'] = art.xpath('.//p[@class="post-item-summary"]/a/img/@src').get()
                published_at_str = art.xpath('.//span[@class="post-meta-item"]/span/text()').get()
                published_at = await str_datetime(published_at_str)
                if published_at:
                    item['created_at'] = published_at
                    item['updated_at'] = published_at

                # 获取详情
                if '/p/' in item['url']:
                    yield response.follow(item['url'], callback=self.parse_detail,
                                        meta={"item": item})
            # 获取下一页
            next_url = response.xpath('//div[@id="pager_bottom"]//a[contains(@class, "current")]/following-sibling::a[1]/@href').get()
            
        ## 获取新闻业文章列表 
        elif submain == "news":
            div_list = response.xpath('//div[@class="news_block"]')
            for div in div_list:
                item = ArticleItem()
                url = div.xpath('.//h2[@class="news_entry"]/a/@href').get()
                item['url'] = f'{parse_url["domain"]}{url}'
                item['title'] = div.xpath('.//h2[@class="news_entry"]/a/text()').get()
                item['description'] = div.xpath('.//div[@class="entry_summary"]/text()[last()]').get()
                item['cover_image'] = div.xpath('.//div[@class="entry_summary"]/a/img/@src').get()
                published_at_str = div.xpath('.//div[@class="entry_footer"]/span[@class="gray"]/text()').get()
                published_at = await str_datetime(published_at_str)
                if published_at:
                    item['created_at'] = published_at
                    item['updated_at'] = published_at
                # 获取详情
                if '/n/' in item['url']:
                    yield response.follow(item['url'], callback=self.parse_detail,
                                        meta={"item": item},cookies=self.cookie)
            next_url = response.xpath('//div[@class="pager"]//a[contains(@class, "current")]/following-sibling::a[1]/@href').get()
        
        self.logger.info(f"🚀🚀🚀🚀🚀next_url:🚀🚀🚀🚀🚀:{next_url}")
        if next_url:
            yield response.follow(next_url, callback=self.parse)
       

    async def parse_detail(self,response):
        try:
            item = response.meta["item"]
            url = response.url
            parse_url = await get_submain(url)
            submain = parse_url["subdomain"]
            if submain == "www":
                content = response.xpath('//div[@class="postBody"]').get()
                if content is None:
                    content = response.xpath('//div[@id="cnblogs_post_body"]').get()
                item["content"] = content
                author_prefix_path = parse_url["path"].split("/")
                author_full_url = f"{parse_url["domain"]}/{author_prefix_path[1]}"
                nickname = await article_author(author_full_url)
                item["nickname"] = nickname
                item["views"] = await article_info(url)
            elif submain == "news":
                item["content"] = response.xpath('//div[@id="news_content"]').get()
                item["nickname"] = response.xpath('//span[@class="news_poster"]/a/text()').get()
                item["views"] = await article_info(url)
            yield item
        except Exception as e:
            self.logger.error(f"🔥🔥🔥parse_detail error: {response.url} 🔥🔥🔥{e}")
            pass