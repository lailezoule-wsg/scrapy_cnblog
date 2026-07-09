# extensions.py
from scrapy import signals
from scrapy.exceptions import NotConfigured

class ItemStatsExtension:
    """统计 Item 抓取成功/失败数量，爬虫结束时输出报告"""

    def __init__(self, stats):
        self.stats = stats
        self.item_scraped_count = 0
        self.item_dropped_count = 0

    @classmethod
    def from_crawler(cls, crawler):
        # 检查是否启用（可选：通过配置开关）
        if not crawler.settings.getbool('ITEM_STATS_ENABLED', True):
            raise NotConfigured('ItemStatsExtension disabled')

        ext = cls(crawler.stats)
        # 连接信号
        crawler.signals.connect(ext.item_scraped, signal=signals.item_scraped)
        crawler.signals.connect(ext.item_dropped, signal=signals.item_dropped)
        crawler.signals.connect(ext.spider_closed, signal=signals.spider_closed)
        return ext

    def item_scraped(self, item, spider):
        """每当一个 Item 成功爬取时调用"""
        self.item_scraped_count += 1
        # 也可以同时更新 stats 收集器
        self.stats.inc_value('my_item_scraped_count')

    def item_dropped(self, item, spider, exception):
        """每当一个 Item 被 Pipeline 丢弃时调用（DropItem）"""
        self.item_dropped_count += 1
        self.stats.inc_value('my_item_dropped_count')

    def spider_closed(self, spider, reason):
        """爬虫关闭时输出汇总报告"""
        spider.logger.info("=" * 50)
        spider.logger.info("📊 爬取统计报告")
        spider.logger.info(f"  成功 Item 数: {self.item_scraped_count}")
        spider.logger.info(f"  丢弃 Item 数: {self.item_dropped_count}")
        spider.logger.info(f"  总计: {self.item_scraped_count + self.item_dropped_count}")
        spider.logger.info("=" * 50)