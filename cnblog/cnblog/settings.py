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

# Concurrency and throttling settings
#CONCURRENT_REQUESTS = 16
# 1. 启用 AutoThrottle 扩展 自动限速
AUTOTHROTTLE_ENABLED = True
# 2. 设置初始下载延迟（可选，默认 5.0 秒）
AUTOTHROTTLE_START_DELAY = 5.0
# 3. 设置最大下载延迟（可选）
AUTOTHROTTLE_MAX_DELAY = 60.0
# 4. 设置目标并发请求数（默认 1.0）
# 这是 AutoThrottle 努力维持的、向每个远程网站发送的平均并发请求数
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# 5. 你仍需要设置并发请求数的硬上限，AutoThrottle 会遵守这个限制
# CONCURRENT_REQUESTS_PER_DOMAIN = 8

CONCURRENT_REQUESTS_PER_DOMAIN = 5

DOWNLOAD_DELAY = 2
RANDOMIZE_DOWNLOAD_DELAY = True      # 默认 True，随机化延迟



# Disable cookies (enabled by default)
#COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers:
#DEFAULT_REQUEST_HEADERS = {
#    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#    "Accept-Language": "en",
#}

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
#SPIDER_MIDDLEWARES = {
#    "cnblog.middlewares.CnblogSpiderMiddleware": 543,
#}

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
DOWNLOADER_MIDDLEWARES = {
    "cnblog.middlewares.CnblogDownloaderMiddleware": 543,
    "scrapy.downloadermiddlewares.offsite.OffsiteMiddleware": None,
}

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
#EXTENSIONS = {
#    "scrapy.extensions.telnet.TelnetConsole": None,
#}

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
   "cnblog.pipelines.CleanPipeline": 278,
   "cnblog.pipelines.ValidatePipeline": 280,
   "cnblog.pipelines.CnblogPipeline": 300,
   "cnblog.pipelines.AsyncDataBasePipeline": 310,
}

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
#AUTOTHROTTLE_ENABLED = True
# The initial download delay
#AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
#AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
#AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
#AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
#HTTPCACHE_ENABLED = True
#HTTPCACHE_EXPIRATION_SECS = 0
#HTTPCACHE_DIR = "httpcache"
#HTTPCACHE_IGNORE_HTTP_CODES = []
#HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

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
