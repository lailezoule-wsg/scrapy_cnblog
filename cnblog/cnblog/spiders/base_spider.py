# cnblog/spiders/base_spider.py
from scrapy.spiders import Spider
from scrapy.statscollectors import StatsCollector
from typing import Any, Dict, Optional, Generator

class BaseParseSpider(Spider):
    """带错误处理的基类爬虫"""
    
    # 声明 stats 属性，告诉类型检查器它存在
    stats: StatsCollector  # ← 添加这一行
    
    def parse_detail(self, response):
        """子类重写此方法"""
        raise NotImplementedError
    
    def handle_parse_error(
        self, 
        response, 
        error: Exception, 
        default_item: Optional[Dict] = None
    ) -> Generator:
        """统一错误处理"""
        self.logger.error(
            f"❌ 解析失败 [{type(error).__name__}]: {response.url} - {error}"
        )
        
        # 现在 stats 被识别了
        if hasattr(self, 'stats'):
            self.stats.inc_value('parse/errors')
            self.stats.inc_value(f'parse/errors/{type(error).__name__}')
        
        # 尝试从 meta 获取 item
        item = response.meta.get('item', {})
        if isinstance(item, dict):
            item['url'] = response.url
            item['_parse_error'] = str(error)
            yield item
        elif default_item:
            default_item['url'] = response.url
            default_item['_parse_error'] = str(error)
            yield default_item
    
    def safe_parse_detail(self, response):
        """安全的解析入口，自动捕获异常"""
        try:
            yield from self.parse_detail(response)
        except Exception as e:
            yield from self.handle_parse_error(response, e)