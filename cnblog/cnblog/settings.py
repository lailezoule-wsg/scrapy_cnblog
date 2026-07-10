# Scrapy settings for cnblog project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html
import os

BOT_NAME = "cnblog"

SPIDER_MODULES = ["cnblog.spiders"]
NEWSPIDER_MODULE = "cnblog.spiders"

ADDONS = {}


# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = "cnblog (+http://www.yourdomain.com)"

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
## 性能调优
# 启用 AutoThrottle 扩展 自动限速
AUTOTHROTTLE_ENABLED = True
# 设置初始下载延迟（可选，默认 5.0 秒）
AUTOTHROTTLE_START_DELAY = 5.0
# 设置最大下载延迟（可选）
AUTOTHROTTLE_MAX_DELAY = 60.0
# 设置目标并发请求数（默认 1.0）
# 这是 AutoThrottle 努力维持的、向每个远程网站发送的平均并发请求数 越高 攻击性越强
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Concurrency and throttling settings
CONCURRENT_REQUESTS = 6
# 你仍需要设置并发请求数的硬上限，AutoThrottle 会遵守这个限制
CONCURRENT_REQUESTS_PER_DOMAIN = 6
# 默认 True，随机化延迟
RANDOMIZE_DOWNLOAD_DELAY = True    
# 下载延迟  
DOWNLOAD_DELAY = 2
# 下载超时
DOWNLOAD_TIMEOUT = 30

# Disable cookies (enabled by default)
"""
COOKIES_ENABLED 开启后
Scrapy 会自动跟踪服务器发送的 Cookie，并在后续请求中带回，就像浏览器一样,适合需要登录的
禁用后，即使在 Request 中通过 headers 手动设置 Cookie 头也不会生效。
如需为特定请求设置 Cookie，应使用 Request 的 cookies 参数
"""
COOKIES_ENABLED = True

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers:
#DEFAULT_REQUEST_HEADERS = {
#    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#    "Accept-Language": "en",
#}

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
SPIDER_MIDDLEWARES = {
   "cnblog.middlewares.CnblogSpiderMiddleware": 543,
}

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
DOWNLOADER_MIDDLEWARES = {
    # "cnblog.middlewares.RandomUserAgentMiddleware": 400,
    "cnblog.middlewares.CnblogDownloaderMiddleware": 543,
    "scrapy.downloadermiddlewares.offsite.OffsiteMiddleware": None,
}

# Enable or disable extensions   加载扩展类
# See https://docs.scrapy.org/en/latest/topics/extensions.html
EXTENSIONS = {
    "cnblog.extensions.ItemStatsExtension.ItemStatsExtension": 500,
    # "scrapy.extensions.telnet.TelnetConsole": None,
}
# 可选：开关控制（默认启用）： 扩展内部的精细化开关，用于在已加载的情况下，决定是否真正执行统计功能， 与上述EXTENSIONS 不同  ；
ITEM_STATS_ENABLED = True

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
   "cnblog.pipelines.CleanPipeline": 278,
   "cnblog.pipelines.ValidatePipeline": 280,
   "cnblog.pipelines.ArticleImagePipeline": 280,
   "cnblog.pipelines.CnblogPipeline": 300,
#    "cnblog.pipelines.AsyncDataBasePipeline": 310,
   "cnblog.pipelines.AsyncBatchDataBasePipeline": 312,
#    "cnblog.pipelines.ArticleJsonWritePipeline": 320,
}

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
"""
HTTP 缓存中间件（HttpCacheMiddleware）就像一个内置的“数据仓库”，可以存储已请求页面的响应。
开启后，再次请求相同的 URL 时，会直接从缓存中读取数据，避免重复下载，大幅提升开发调试的效率。
"""
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 4 * 60 * 60  # 4h
HTTPCACHE_DIR = "httpcache"
HTTPCACHE_IGNORE_HTTP_CODES = [404,500]
HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# Set settings whose default value is deprecated to a future-proof value
FEED_EXPORT_ENCODING = "utf-8"

# 数据库连接配置（请替换为你的实际信息）
POSTGRESQL_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'postgres',
    'password': 'postgres',
    'database': 'cnblog',
    # 'dsn': 'postgresql://user:pass@localhost:5432/db' # 也可用 DSN 字符串
}
"""
DB_BATCH_SIZE 数值配置问题
问题：如果你开启了极高的并发（比如 CONCURRENT_REQUESTS = 10），同一时刻会发出 10 个详情页请求，它们返回的顺序是乱序的。
你没法保证先回来的 20 个请求恰好属于同一个逻辑批次。
对策（推荐方案）：不要在此时强行按“数量”批次提交，而是按“请求 URL 指纹”或“时间窗口”提交。如果必须按数量，请务必将 batch_size 调得足够大（比如 200），
覆盖大部分并发返回的数据，并在日志中记录 max_processed_url。
对于这种乱序场景，使用增量更新时间戳（Upsert）比死磕“分页边界”更稳妥——因为即使断点乱了，ON CONFLICT 也能帮你自动覆盖或忽略已存在的记录

CONCURRENT_REQUESTS = 1时 ： 可以和一次深度查询的数据量一致，否则导致爬取边界不清晰问题（数据碎片化）
"""
DB_BATCH_SIZE = 100

# 【重要】启用 asyncio 支持
TWISTED_REACTOR = 'twisted.internet.asyncioreactor.AsyncioSelectorReactor'

# 日志
LOG_LEVEL = 'INFO'  # 生产环境中通常建议设置为 LOG_LEVEL = 'INFO' 以减少日志量，但保留错误和警告信息
# LOG_FILE = 'logs/cnblog.log'
# LOG_DIR = os.path.dirname(LOG_FILE)
# if LOG_DIR and not os.path.exists(LOG_DIR):
#     os.makedirs(LOG_DIR)

# Playwright
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    # "http": "scrapy_playwright_stealth.handler.ScrapyPlaywrightStealthDownloadHandler",
    # "https": "scrapy_playwright_stealth.handler.ScrapyPlaywrightStealthDownloadHandler",
}
# （可选）设置 Playwright 的默认参数，如超时、无头模式等
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": False,  # 调试时可设为 False，观察浏览器行为
}

# (可选) 设置最大并发上下文数
PLAYWRIGHT_MAX_CONTEXTS = 8  # [reference:6]
# 不限制
# DEPTH_LIMIT = 0  

# 图片配置 固定名称 ImagePipeline会自动获取
IMAGES_STORE = "data/cover_images"
IMAGES_STORE_DIR = os.path.dirname(IMAGES_STORE)
if IMAGES_STORE_DIR and not os.path.exists(IMAGES_STORE_DIR):
    os.makedirs(IMAGES_STORE_DIR)

# 3. 缩略图配置（可选，会覆盖 Pipeline 中的默认值）
# IMAGES_THUMBS = {
#     'small': (100, 100),
#     'medium': (300, 300),
#     'large': (600, 600),
# }
IMAGES_EXT = {'jpg', 'jpeg', 'png', 'gif'}
# 图片最小尺寸过滤（可选） 0 ：不限制
IMAGES_MIN_WIDTH = 0
IMAGES_MIN_HEIGHT = 0
# 有效时间 (每次ImagesPipeline下载图片前执行清理)
IMAGES_EXPIRES = 2



