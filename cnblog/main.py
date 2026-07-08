# run.py —— 脚本方式运行
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from cnblog.spiders.article import ArticleSpider

if __name__ == "__main__":
    process = CrawlerProcess(get_project_settings())
    process.crawl(ArticleSpider)
    process.start()