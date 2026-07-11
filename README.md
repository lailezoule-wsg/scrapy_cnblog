# scrapy_cnblog

基于 Scrapy + Playwright 的博客园异步爬虫系统。抓取 [博客园](https://www.cnblogs.com/) 的社区文章与科技新闻，通过 Redis Cookie 连接池 + Playwright 自动化登录解决认证问题，全链路异步写入 PostgreSQL。

## 项目结构

```
scrapy_cnblog/
├── cnblog/
│   ├── scrapy.cfg                         # Scrapy 部署配置
│   ├── main.py                            # 启动入口
│   └── cnblog/
│       ├── settings.py                    # 核心配置
│       ├── items.py                       # 数据模型（ArticleItem）
│       ├── loaders.py                     # ItemLoader 数据加载器（字段预处理与清洗）
│       ├── pipelines.py                   # 数据管道（清洗 → 校验 → 图片下载 → 批量入库）
│       ├── middlewares.py                 # 下载/Spider 中间件
│       ├── core/
│       │   ├── cookies.js                 # 静态 Cookie（JSON 数组）
│       │   ├── user_info.js               # 登录账号配置（JSON 数组）
│       │   ├── cookie_manager.py          # 同步 Redis Cookie 池
│       │   ├── async_cookie_manager.py    # 异步 Redis Cookie 池
│       │   ├── login_generator.py         # Playwright 自动化登录
│       │   └── json_encode.py             # 自定义 JSON 编码器（datetime 序列化）
│       ├── extensions/
│       │   └── ItemStatsExtension.py      # 爬取统计扩展（成功/失败/汇总报告）
│       ├── utils/
│       │   └── common.py                  # 工具函数（AJAX 请求、URL 解析、Cookie 工具）
│       └── spiders/
│           ├── article.py                 # 核心爬虫（ArticleSpider，手动翻页）
│           └── articl_crawl.py            # CrawlSpider 变体（Rules + ItemLoader 自动翻页）
├── requirements.txt
└── README.md
```

## 核心功能

| 模块                   | 说明                                                                                                            |
| ---------------------- | --------------------------------------------------------------------------------------------------------------- |
| **全链路异步**         | `AsyncioSelectorReactor` 驱动，Spider 回调、httpx AJAX 请求、asyncpg 入库全程 `async/await` 非阻塞              |
| **Playwright 渲染**    | 集成 `scrapy-playwright`，Chromium 渲染 JS 动态页面，有头模式便于调试                                           |
| **Redis Cookie 池**    | 同步/异步双版本，支持多账号存储、随机选取、`SCAN + MGET` 批量迭代、生成器逐条迭代                               |
| **自动化登录**         | `LoginGenerator` 模拟登录博客园，反检测（覆盖 `webdriver`、伪造浏览器指纹），多账号轮询 + 重试 + reCAPTCHA 检测 |
| **双 Spider 实现**     | `ArticleSpider`（手动 XPath 翻页）与 `ArticleCrawlSpider`（CrawlSpider Rules + ItemLoader 自动翻页）两种模式    |
| **ItemLoader 数据加载**| `ArticleLoader` 封装字段预处理：空白清洗、日期解析、图片 URL 补全、阅读量转整型                                |
| **图片下载**           | `ArticleImagePipeline` 自动下载封面图到本地，自定义存储路径（按文章标题分目录）                                 |
| **批量异步入库**       | `AsyncBatchDataBasePipeline` 缓冲满 `DB_BATCH_SIZE`（100）条后批量 INSERT，减少数据库交互次数                   |
| **UPSERT 去重**        | `INSERT ... ON CONFLICT (url) DO UPDATE`，重复抓取自动更新                                                      |
| **爬取统计**           | `ItemStatsExtension` 实时统计 scraped/dropped 数量，爬虫结束时输出汇总报告                                      |
| **礼貌爬取**           | AutoThrottle 自适应限速 + 随机延迟 + 域名级并发控制 + 遵守 robots.txt                                           |

## 数据流程

```
Playwright (Chromium) 渲染页面
        │
        ▼
  ArticleSpider.parse()          解析博客/新闻列表页，自动翻页
  或 ArticleCrawlSpider          CrawlSpider Rules + LinkExtractor 自动翻页
        │
        ▼
  parse_detail()                 提取正文，httpx 异步请求 AJAX 补全作者与阅读量
        │                         新闻板块自动从 Redis Cookie 池获取认证
        ▼
  Item Pipeline
    ├─ CleanPipeline             字段清洗（去除空白字符串）
    ├─ ValidatePipeline          数据校验（丢弃缺少 title/description 的条目）
    ├─ ArticleImagePipeline      封面图下载到本地（data/cover_images/）
    ├─ CnblogPipeline            透传处理
    └─ AsyncBatchDataBasePipeline  批量 asyncpg 连接池写入 PostgreSQL（UPSERT 去重）
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
playwright install
```

### 2. 启动服务

- **PostgreSQL**：`CREATE DATABASE cnblog;`（表由 Pipeline 自动创建）
- **Redis**：确保本地运行中（默认 `localhost:6379`）

数据库连接配置位于 `settings.py` 的 `POSTGRESQL_CONFIG`。

### 3. 配置认证（可选）

博客文章板块无需认证，可直接抓取。新闻板块需认证 Cookie，两种方式：

**方式一：自动化登录**（推荐）

在 `core/user_info.js` 中填写账号，执行后 Cookie 自动存入 Redis：

```json
[{ "username": "your_username", "password": "your_password" }]
```

```bash
python cnblog/cnblog/core/login_generator.py
```

**方式二：手动配置**

在 `core/cookies.js` 中直接粘贴 Cookie 字符串。

### 4. 启动爬虫

在 `cnblog/` 目录（含 `scrapy.cfg`）下执行：

```bash
python main.py
# 或
scrapy crawl article        # ArticleSpider（手动翻页）
scrapy crawl article_crawl  # ArticleCrawlSpider（CrawlSpider + ItemLoader）
```

## 数据库表结构

`articles` 表由 Pipeline 自动创建：

| 字段                 | 类型                | 说明                          |
| -------------------- | ------------------- | ----------------------------- |
| `id`                 | BIGSERIAL           | 主键                          |
| `url`                | VARCHAR(500) UNIQUE | 文章链接（去重依据）          |
| `title`              | VARCHAR             | 标题                          |
| `nickname`           | VARCHAR             | 作者昵称                      |
| `views`              | INTEGER             | 阅读量                        |
| `description`        | VARCHAR             | 摘要                          |
| `content`            | TEXT                | 正文 HTML                     |
| `cover_image`        | VARCHAR             | 封面图链接                    |
| `cover_image_local`  | VARCHAR             | 封面图本地路径                |
| `created_at`         | TIMESTAMP           | 发布时间                      |
| `updated_at`         | TIMESTAMP           | 更新时间（UPSERT 时自动刷新） |

## 配置说明

关键配置项位于 `cnblog/cnblog/settings.py`：

| 配置项                        | 默认值             | 说明                                    |
| ----------------------------- | ------------------ | --------------------------------------- |
| `CONCURRENT_REQUESTS`         | `6`                | 全局并发请求数                          |
| `CONCURRENT_REQUESTS_PER_DOMAIN` | `5`             | 单域名并发请求数                        |
| `DOWNLOAD_DELAY`              | `2`                | 下载延迟（秒），启用随机化              |
| `AUTOTHROTTLE_ENABLED`        | `True`             | 自适应限速                              |
| `DB_BATCH_SIZE`               | `100`              | 批量入库缓冲区大小                      |
| `POSTGRESQL_CONFIG`           | localhost:5432     | PostgreSQL 连接配置                     |
| `PLAYWRIGHT_LAUNCH_OPTIONS`   | `headless: False`  | Playwright 浏览器启动选项               |
| `PLAYWRIGHT_MAX_CONTEXTS`     | `8`                | Playwright 最大上下文数                 |
| `IMAGES_STORE`                | `data/cover_images`| 封面图本地存储目录                      |
| `ITEM_STATS_ENABLED`          | `True`             | 爬取统计扩展开关                        |

## 依赖

| 包                  | 版本   | 用途                          |
| ------------------- | ------ | ----------------------------- |
| `scrapy`            | 2.16.0 | 爬虫框架                      |
| `scrapy-playwright` | 0.0.47 | Playwright 下载处理器         |
| `playwright`        | 1.52.0 | 浏览器自动化（登录）          |
| `asyncpg`           | 0.31.0 | 异步 PostgreSQL 驱动          |
| `httpx`             | 0.28.1 | 异步 HTTP 客户端              |
| `redis`             | 6.4.0  | Redis 客户端（Cookie 连接池） |
| `tldextract`        | 5.3.1  | 域名解析                      |
| `lxml`              | 6.0.4  | HTML 解析                     |
| `pytz`              | 2026.2 | 时区处理                      |
| `itemadapter`       | 0.13.1 | Item 字段抽象                 |
| `itemloaders`       | 1.3.2  | ItemLoader 数据加载器         |
| `Pillow`            | 11.2.1 | 图片处理（ImagesPipeline）    |
| `typing_extensions` | 4.14.1 | 类型提示扩展                  |
