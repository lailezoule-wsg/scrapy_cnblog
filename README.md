# scrapy_cnblog

基于 Scrapy + Playwright 的博客园异步爬虫系统。抓取 [博客园](https://www.cnblogs.com/) 的社区文章与科技新闻，通过 Redis Cookie 连接池 + Playwright 自动化登录解决认证问题，全链路异步写入 PostgreSQL。

## 项目结构

```
CnBlog/
├── cnblog/
│   ├── scrapy.cfg                    # Scrapy 部署配置
│   ├── main.py                       # 启动入口
│   ├── scripts/
│   │   ├── cookies.js                # 静态 Cookie（JSON 数组）
│   │   ├── user_info.js              # 登录账号配置（JSON 数组）
│   │   ├── cookie_manager.py         # 同步 Redis Cookie 池
│   │   ├── async_cookie_manager.py   # 异步 Redis Cookie 池
│   │   └── login_generator.py        # Playwright 自动化登录
│   └── cnblog/
│       ├── settings.py               # 核心配置
│       ├── items.py                  # 数据模型（ArticleItem）
│       ├── pipelines.py              # 数据管道（清洗 → 校验 → 异步入库）
│       ├── middlewares.py            # 下载中间件
│       ├── utils/
│       │   └── common.py             # 工具函数
│       └── spiders/
│           └── article.py            # 核心爬虫（ArticleSpider）
├── requirements.txt
└── README.md
```

## 核心功能

| 模块                | 说明                                                                                                            |
| ------------------- | --------------------------------------------------------------------------------------------------------------- |
| **全链路异步**      | `AsyncioSelectorReactor` 驱动，Spider 回调、httpx AJAX 请求、asyncpg 入库全程 `async/await` 非阻塞              |
| **Playwright 渲染** | 集成 `scrapy-playwright`，Chromium 渲染 JS 动态页面，有头模式便于调试                                           |
| **Redis Cookie 池** | 同步/异步双版本，支持多账号存储、随机选取、`SCAN + MGET` 批量迭代、生成器逐条迭代                               |
| **自动化登录**      | `LoginGenerator` 模拟登录博客园，反检测（覆盖 `webdriver`、伪造浏览器指纹），多账号轮询 + 重试 + reCAPTCHA 检测 |
| **UPSERT 去重**     | `INSERT ... ON CONFLICT (url) DO UPDATE`，重复抓取自动更新                                                      |
| **礼貌爬取**        | AutoThrottle 自适应限速 + 随机延迟 + 域名级并发控制 + 遵守 robots.txt                                           |

## 数据流程

```
Playwright (Chromium) 渲染页面
        │
        ▼
  ArticleSpider.parse()          解析博客/新闻列表页，自动翻页
        │
        ▼
  parse_detail()                 提取正文，httpx 异步请求 AJAX 补全作者与阅读量
        │                         新闻板块自动从 Redis Cookie 池获取认证
        ▼
  Item Pipeline
    ├─ CleanPipeline             字段清洗
    ├─ ValidatePipeline          数据校验
    └─ AsyncDataBasePipeline     asyncpg 连接池写入 PostgreSQL（UPSERT 去重）
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

在 `scripts/user_info.js` 中填写账号，执行后 Cookie 自动存入 Redis：

```json
[{ "username": "your_username", "password": "your_password" }]
```

```bash
python cnblog/scripts/login_generator.py
```

**方式二：手动配置**

在 `scripts/cookies.js` 中直接粘贴 Cookie 字符串。

### 4. 启动爬虫

在 `cnblog/` 目录（含 `scrapy.cfg`）下执行：

```bash
python main.py
# 或
scrapy crawl article
```

## 数据库表结构

`articles` 表由 Pipeline 自动创建：

| 字段          | 类型                | 说明                          |
| ------------- | ------------------- | ----------------------------- |
| `id`          | BIGSERIAL           | 主键                          |
| `url`         | VARCHAR(500) UNIQUE | 文章链接（去重依据）          |
| `title`       | VARCHAR             | 标题                          |
| `nickname`    | VARCHAR             | 作者昵称                      |
| `views`       | VARCHAR             | 阅读量                        |
| `description` | VARCHAR             | 摘要                          |
| `content`     | TEXT                | 正文 HTML                     |
| `cover_image` | VARCHAR             | 封面图链接                    |
| `created_at`  | TIMESTAMP           | 发布时间                      |
| `updated_at`  | TIMESTAMP           | 更新时间（UPSERT 时自动刷新） |

## 依赖

| 包                  | 版本   | 用途                          |
| ------------------- | ------ | ----------------------------- |
| `scrapy`            | 2.16.0 | 爬虫框架                      |
| `scrapy-playwright` | 0.0.47 | Playwright 下载处理器         |
| `asyncpg`           | 0.31.0 | 异步 PostgreSQL 驱动          |
| `httpx`             | 0.28.1 | 异步 HTTP 客户端              |
| `redis`             | 6.4.0  | Redis 客户端（Cookie 连接池） |
| `tldextract`        | 5.3.1  | 域名解析                      |
| `lxml`              | 6.0.4  | HTML 解析                     |
| `pytz`              | 2026.2 | 时区处理                      |
| `itemadapter`       | 0.13.1 | Item 字段抽象                 |
| `parsel`            | 1.11.0 | XPath/CSS 选择器              |
