import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from cnblog.loaders import ArticleLoader
from cnblog.items import ArticleItem
from cnblog.core.cookie_manager import CookieManager
from cnblog.utils.common import article_author, article_info, get_submain, str_datetime


class ArticleCrawlSpider(CrawlSpider):
    name = 'article_crawl'
    allowed_domains = ['www.cnblogs.com', 'news.cnblogs.com']
    start_urls = ['https://www.cnblogs.com/', 'https://news.cnblogs.com/']

    cookieManager = CookieManager()
    cookie = cookieManager.get_random_cookie(name)

    # Rule 只负责分页跟踪，不匹配详情页链接
    rules = (
        # 博客分页：跟踪 pager 中的翻页链接
        Rule(
            LinkExtractor(restrict_css='div#pager_bottom a'),
            callback= "parse_list",
            follow=True,
        ),
        # 新闻分页：跟踪 pager 中的翻页链接
        Rule(
            LinkExtractor(restrict_css='div.pager a'),
            callback= "parse_list",
            follow=True,
        ),
    )

    async def parse_list(self, response):
        """
        CrawlSpider 对 start_urls 和 follow=True 到达的页面都会调用此方法。
        在这里解析列表页，提取基础字段，手动 yield Request 到详情页。
        """
        parse_url = await get_submain(response.url)
        submain = parse_url["subdomain"]

        if submain == "www":
            for art in response.xpath('//article[@class="post-item"]'):
                loader = ArticleLoader(item=ArticleItem(), selector=art)
                loader.add_xpath('title', './/a[@class="post-item-title"]/text()')
                loader.add_xpath('url', './/a[@class="post-item-title"]/@href')
                loader.add_xpath('description', './/p[@class="post-item-summary"]/text()[last()]')
                loader.add_xpath('cover_image', './/p[@class="post-item-summary"]/a/img/@src')
                loader.add_xpath('created_at', './/span[@class="post-meta-item"]/span/text()')
                item = loader.load_item()

                detail_url = art.xpath('.//a[@class="post-item-title"]/@href').get()
                if detail_url and '/p/' in detail_url:
                    yield response.follow(
                        detail_url,
                        callback=self.parse_detail,
                        meta={'item': item},
                    )

        elif submain == "news":
            for div in response.xpath('//div[@class="news_block"]'):
                loader = ArticleLoader(item=ArticleItem(), selector=div)
                loader.add_xpath('title', './/h2[@class="news_entry"]/a/text()')
                loader.add_xpath('url', './/h2[@class="news_entry"]/a/@href')
                loader.add_xpath('description', './/div[@class="entry_summary"]/text()[last()]')
                loader.add_xpath('cover_image', './/div[@class="entry_summary"]/a/img/@src')
                loader.add_xpath('created_at', './/div[@class="entry_footer"]/span[@class="gray"]/text()')
                item = loader.load_item()

                detail_url = div.xpath('.//h2[@class="news_entry"]/a/@href').get()
                if detail_url and '/n/' in detail_url:
                    yield response.follow(
                        detail_url,
                        callback=self.parse_detail,
                        meta={'item': item},
                        cookies=self.cookie,
                    )

    async def parse_detail(self, response):
        """阶段二：从详情页补全 content, nickname, views"""
        item = response.meta['item']
        parse_url = await get_submain(response.url)
        submain = parse_url["subdomain"]

        if submain == "www":
            content = response.xpath('//div[@class="postBody"]').get()
            if content is None:
                content = response.xpath('//div[@id="cnblogs_post_body"]').get()
            item['content'] = content

            author_prefix = parse_url["path"].split("/")[1]
            author_full_url = f"{parse_url['domain']}/{author_prefix}"
            item['nickname'] = await article_author(author_full_url)
            item['views'] = await article_info(response.url)

        elif submain == "news":
            item['content'] = response.xpath('//div[@id="news_content"]').get()
            item['nickname'] = response.xpath('//span[@class="news_poster"]/a/text()').get()
            item['views'] = await article_info(response.url)

        yield item