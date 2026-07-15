# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from os import PathLike
from typing_extensions import Self
from typing import Iterable
import json
import warnings
import hashlib
import asyncpg
import scrapy
from scrapy.crawler import Crawler
from scrapy.exceptions import ScrapyDeprecationWarning
# ItemAdapter:Scrapy 统一接口包装器
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem
from cnblog.items import ArticleItem
from scrapy.pipelines.images import ImagesPipeline,ImageException
from scrapy.http import Request, Response
from twisted.python.failure import Failure
from scrapy.pipelines.files import FileException
from cnblog.core.json_encode import ArticleTimeJSONEncoder

warnings.filterwarnings(
    "ignore",
    category=ScrapyDeprecationWarning,
    module="scrapy.pipelines"   # 只屏蔽 scrapy.pipelines 模块的该警告
)

class CnblogPipeline:

    def process_item(self, item, spider):
        return item

# 数据清洗
class CleanPipeline:

    def process_item(self,item,spider):
        # spider.logger.warning("🚀🚀  CleanPipeline......................")
        adapter = ItemAdapter(item)
        # adapter.items():处理yield出来的数据；只处理传过来，需要处理的
        # adapter.field_name():以item管道定义的原始数据
        for field,value in adapter.items():
            if isinstance(value,str):
                adapter[field] = value.strip()
        # 可以在此处加验证 或者单独一个类
        return item

class ValidatePipeline:
    """数据验证"""
    
    def process_item(self, item, spider):
        # spider.logger.warning("🚀🚀  ValidatePipeline......................")
        adapter = ItemAdapter(item)
        if not adapter.get("title"):
            raise DropItem("Missing title")
        if not adapter.get("description"):
            raise DropItem("Missing description")
        return item

from scrapy.pipelines.media import  MediaPipeline

class ArticleImagePipeline(ImagesPipeline):
    """封面图下载"""
    def get_media_requests(self,item,info) :  # type: ignore[override]
        adapter = ItemAdapter(item)
        cover_image = adapter.get('cover_image', [])
        info.spider.logger.warning(f"🚄🚄🚄🚄 封面图下载:{cover_image}")
        if not cover_image:
            return []
        # 确保是列表
        if isinstance(cover_image, str):
            cover_image = [cover_image]
        for index, url in enumerate(cover_image):
            if not url:
                continue
            # if url.startswith("//"):
            #     url = f"https:{url}"
            yield scrapy.Request(
                    url,
                    meta={
                        'item': dict(adapter),
                        'index': index,
                    }
                )
    # scrapy 会根据file_path 的返回路径是否存在缓存中 确定是否要重新下载
    def file_path(self, request, response=None, info=MediaPipeline.SpiderInfo | None, *, item=None):
        """自定义图片保存路径和文件名"""
        # 示例：按文章标题分类存储
        item_data = request.meta.get('item', {})
        title = item_data.get('title', 'unknown')
        # 清理非法字符
        import re
        safe_title = re.sub(r'[\\/*?:"<>|]', '_', title)
        # 从 URL 提取扩展名
        extension = request.url.split('.')[-1]
        if extension not in ('jpg', 'jpeg', 'png', 'gif'):
            extension = 'jpg'
        return f'{safe_title}/{hashlib.md5(request.url.encode()).hexdigest()[:8]}.{extension}'

    def item_completed(self, results, item, info):
        """当所有图片下载完成后调用，results 是一个列表，每个元素为 (success, data)"""
        # results: [(True, {'url': ..., 'path': ..., 'checksum': ...}), (False, ...)]
        adapter = ItemAdapter(item)
         # 提取成功下载的本地路径
        local_paths = []
        # local_paths = [data['path'] for success, data in results if success and isinstance(data, dict)]
        try:
            # results 元组列表 [(success,data),(success,data),(success,data)]  success: bool  data:dict | Failure
            for success, data in results:
                if success and isinstance(data, dict):
                    local_paths.append(data['path'])
                    info.spider.logger.warning(f"🚄🚄🚄🚄图片下载成功: {data}")
                else:
                    # 失败或数据异常
                    if isinstance(data, Failure):
                        # 获取异常类型和异常消息
                        exc_type = data.type           # 异常类，如 FileException
                        exc_value = data.value         # 异常实例
                        # exc_traceback = data.getTraceback()  # 完整堆栈字符串
                        info.spider.logger.error(f"🚄🚄🚄🚄图片下载失败: {type(data.value).__name__}: {exc_value}")
                    else:
                        info.spider.logger.warning(f"🚄🚄🚄🚄图片下载失败3: {data}")
        except FileException as e:
            info.spider.logger.warning(f"🚄🚄🚄🚄图片下载失败: {str(e)}")
            pass
        except Exception as e:
            info.spider.logger.warning(f"🚄🚄🚄🚄图片下载失败: {str(e)}")
            pass
        # 将本地路径列表保存到 item 中
        # 获取原始字段，并设置默认值为空列表
        if local_paths:
            # 如果原始字段是单个字符串，这里保存第一个路径
            # 如果原始是列表，则保存列表
            original = adapter.get('cover_image')
            if isinstance(original, str):
                adapter['cover_image_local'] = local_paths[0] if local_paths else ''
            else:
                adapter['cover_image_local'] = ",".join(local_paths)
        else:
            adapter['cover_image_local'] = ""
        return item
    
class ArticleJsonWritePipeline:
    async def open_spider(self, spider):
        self.file = open(f'{spider.name}_data.json', 'w', encoding='utf-8')
        self.file.write('[')
        self.first_item = True
    async def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        line = json.dumps(dict(adapter), ensure_ascii=False,cls=ArticleTimeJSONEncoder)
        if not self.first_item:
            self.file.write(',')
        self.file.write(line)
        self.first_item = False
        return item
    async def close_spider(self, spider):
        self.file.write(']')
        self.file.close()

# 单条数据插入
class AsyncDataBasePipeline:
    """异步数据库管道（协程管道）"""
    # 动态映射配置
    TABLE_CONFIG = {
        ArticleItem:{
            "table":"articles",
            # 插入数据
            "columns":["title","description","url","nickname","views","content","cover_image","cover_image_local"],
             # 冲突处理：指定唯一约束列（例如 url），若为 None 则不处理冲突
            "conflict_column": "url",
            # 冲突时更新的列（不含 created_at 等不需要更新的列）
            "update_columns": ["title", "description","nickname","views","content", "cover_image", "cover_image_local", "updated_at"],
            # 建表 SQL（包含 TIMESTAMPTZ 和默认值）
            "create_sql": """
                CREATE TABLE IF NOT EXISTS articles (
                    id BIGSERIAL PRIMARY KEY,
                    url VARCHAR(500) UNIQUE,
                    title VARCHAR(500),
                    nickname VARCHAR(64),
                    views INT DEFAULT 0,
                    description VARCHAR(500),
                    content TEXT,
                    cover_image VARCHAR(500),
                    cover_image_local VARCHAR(500),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url);
            """,
        }
    }

    def __init__(self, config):
        self.config = config
        self.pool = None

    @classmethod
    def from_crawler(cls, crawler):
        """从 crawler 的设置中读取数据库配置"""
        config = crawler.settings.get('POSTGRESQL_CONFIG')
        if not config:
            raise ValueError("POSTGRESQL_CONFIG not found in settings")
        return cls(config)
    
    async def open_spider(self, spider):
        """爬虫开启时，创建数据库连接池"""
        try:
            # asyncpg 是 Python 生态中为 PostgreSQL 和 asyncio 框架设计的高性能异步数据库驱动
            self.pool = await asyncpg.create_pool(
                **self.config,
                min_size=5,
                max_size=20,
                command_timeout=60,          # 命令超时，防止长连接被服务端断开
                max_inactive_connection_lifetime=300,  # 5分钟空闲后回收连接
            ) #[reference:4]
            spider.logger.info(f"Connected to PostgreSQL: {self.config.get('database')}")
        except Exception as e:
            spider.logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
        # 建表：遍历所有配置，执行 create_sql
        async with self.pool.acquire() as conn:
            for item_cls, cfg in self.TABLE_CONFIG.items():
                create_sql = cfg.get("create_sql")
                if create_sql:
                    try:
                        await conn.execute(create_sql)
                        spider.logger.info(f"Table {cfg['table']} checked/created.")
                    except Exception as e:
                        spider.logger.error(f"Failed to create table {cfg['table']}: {e}")
                        raise  # 建表失败终止爬虫

    async def close_spider(self, spider):
        """爬虫关闭时，释放连接池资源"""
        try:
            if self.pool:
                await self.pool.close()
                spider.logger.info("PostgreSQL connection pool closed.")
        except Exception as e:
            spider.logger.error(f"PostgreSQL closed Error in spider_closed: {e}")


    async def process_item(self,item,spider):
        spider.logger.warning("🚀🚀 AsyncDataBasePipeline")
        """根据 Item 类型路由到对应的表插入/更新"""
        # if self.pool is None:
        #     raise RuntimeError("Database pool is not initialized. Ensure open_spider succeeded.")

        ## 上下两种写法均可
        assert self.pool is not None, "Pool not initialized"

        item_cls = type(item)
        cfg = self.TABLE_CONFIG.get(item_cls)
        if not cfg:
            spider.logger.warning(f"No table config for {type(item).__name__}, dropping item")
            raise DropItem(f"No table config for {type(item).__name__}")
        
         # 标准化 columns 配置（支持 list 或 dict）
        col_config = cfg["columns"]
        if isinstance(col_config, list):
            columns = col_config
            item_fields = col_config
        elif isinstance(col_config, dict):
            columns = list(col_config.values())
            item_fields = list(col_config.keys())
        else:
            raise TypeError(f"Invalid columns config for {cfg['table']}: must be dict or list")

        table = cfg["table"]
        # 提取值
        values = [item.get(field) for field in item_fields]

        # 构建 SQL 语句
        placeholders = ", ".join([f"${i+1}" for i in range(len(columns))])
        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"

        # 处理 ON CONFLICT
        conflict_col = cfg.get("conflict_column")
        if conflict_col:
            update_cols = cfg.get("update_columns", [])
            if update_cols:
                # 构建 UPDATE SET 子句，特殊处理 updated_at
                set_clauses = []
                for col in update_cols:
                    if col == "updated_at":
                        set_clauses.append(f"{col} = CURRENT_TIMESTAMP")
                    else:
                        set_clauses.append(f"{col} = EXCLUDED.{col}")
                sql += f" ON CONFLICT ({conflict_col}) DO UPDATE SET {', '.join(set_clauses)}"
            else:
                sql += f" ON CONFLICT ({conflict_col}) DO NOTHING"

        # 执行 SQL
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(sql, *values)
        except Exception as e:
            spider.logger.error(f"Database error for {table}: {e}, item: {item}")
            raise

        return item

# 批量数据插入
class AsyncBatchDataBasePipeline:
    TABLE_CONFIG = {
        ArticleItem: {
            "table": "articles",
            "columns": ["title", "description", "url", "nickname", "views", 
                        "content", "cover_image", "cover_image_local"],
            "conflict_column": "url",
            "update_columns": ["title", "description", "nickname", "views", 
                               "content", "cover_image", "cover_image_local", "updated_at"],
            "create_sql": """
                CREATE TABLE IF NOT EXISTS articles (
                    id BIGSERIAL PRIMARY KEY,
                    url VARCHAR(500) UNIQUE,
                    title VARCHAR(500),
                    nickname VARCHAR(64),
                    views INT DEFAULT 0,
                    description VARCHAR(500),
                    content TEXT,
                    cover_image VARCHAR(500),
                    cover_image_local VARCHAR(500),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url);
            """,
        }
    }

    def __init__(self, config,batch_size = 100):
        self.config = config
        self.batch_size = batch_size          # 每批次最大条数
        self.pool = None
        self._cache = {}                      # {item_cls: [ (values, item), ... ]}
        self._sql_templates = {}              # 缓存各表的预编译SQL模板

    @classmethod
    def from_crawler(cls, crawler):
        config = crawler.settings.get('POSTGRESQL_CONFIG')
        if not config:
            raise ValueError("POSTGRESQL_CONFIG not found in settings")
        batch_size = crawler.settings.get('DB_BATCH_SIZE', 100)
        return cls(config, batch_size)

    async def open_spider(self, spider):
        """创建连接池并建表"""
        self.pool = await asyncpg.create_pool(
            **self.config,
            min_size=5,
            max_size=20,
            command_timeout=60,
            max_inactive_connection_lifetime=300,
        )
        spider.logger.info(f"Connected to PostgreSQL: {self.config.get('database')}")

        # 建表（可考虑移到外部，但保留在这里也可以）
        async with self.pool.acquire() as conn:
            for item_cls, cfg in self.TABLE_CONFIG.items():
                create_sql = cfg.get("create_sql")
                if create_sql:
                    await conn.execute(create_sql)
                    spider.logger.info(f"Table {cfg['table']} checked/created.")

    async def close_spider(self, spider):
        """关闭前刷新所有缓存"""
        await self._flush_all(spider)
        if self.pool:
            await self.pool.close()
            spider.logger.info("PostgreSQL connection pool closed.")

    async def process_item(self, item, spider):
        """将 Item 加入缓存，达到阈值时刷新"""
        item_cls = type(item)
        cfg = self.TABLE_CONFIG.get(item_cls)
        if not cfg:
            spider.logger.warning(f"No table config for {item_cls.__name__}, dropping item")
            raise DropItem(f"No table config for {item_cls.__name__}")

        # 提取字段和值
        col_config = cfg["columns"]
        if isinstance(col_config, list):
            columns = col_config
            item_fields = col_config
        elif isinstance(col_config, dict):
            columns = list(col_config.values())
            item_fields = list(col_config.keys())
        else:
            raise TypeError(f"Invalid columns config for {cfg['table']}")

        # 提取值（此处可做类型转换，如 list -> str）
        adapter = ItemAdapter(item)
        values = [adapter.get(field) for field in item_fields]

        # 存入缓存
        cache_key = item_cls
        if cache_key not in self._cache:
            self._cache[cache_key] = []
        self._cache[cache_key].append((values, item))  # 保存 item 用于日志

        # 达到阈值则刷新该类型
        if len(self._cache[cache_key]) >= self.batch_size:
            await self._flush(cache_key, spider)

        return item

    async def _flush(self, item_cls, spider):
        """批量写入指定类型的缓存数据"""
        cache = self._cache.get(item_cls, [])
        if not cache:
            return

        cfg = self.TABLE_CONFIG[item_cls]
        table = cfg["table"]
        columns = cfg["columns"] if isinstance(cfg["columns"], list) else list(cfg["columns"].values())
        conflict_col = cfg.get("conflict_column")
        update_cols = cfg.get("update_columns", [])

        # 构造批量插入 SQL（一次执行多行）
        sql = self._build_batch_insert_sql(table, columns, conflict_col, update_cols, len(cache))
        # 展平所有参数
        flat_params = []
        for values, _ in cache:
            flat_params.extend(values)

        assert self.pool is not None, "Pool not initialized"

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(sql, *flat_params)
            spider.logger.debug(f"Batch inserted {len(cache)} rows into {table}")
        except Exception as e:
            spider.logger.error(f"Batch insert failed for {table}: {e}")
            # 可选：降级为逐条插入（或记录失败数据）
            # 此处直接抛出，中断爬虫（可根据需要改为重试或丢弃）
            raise
        finally:
            # 清空缓存
            self._cache[item_cls] = []

    def _build_batch_insert_sql(self, table, columns, conflict_col, update_cols, batch_size):
        """生成批量插入 SQL，包含 ON CONFLICT 子句"""
        num_cols = len(columns)
        # 构造 VALUES 部分: ($1, $2, ...), ($3, $4, ...), ...
        value_parts = []
        param_idx = 1
        for _ in range(batch_size):
            placeholders = ', '.join([f'${param_idx + i}' for i in range(num_cols)])
            value_parts.append(f'({placeholders})')
            param_idx += num_cols

        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES {', '.join(value_parts)}"

        if conflict_col:
            if update_cols:
                set_clauses = []
                for col in update_cols:
                    if col == "updated_at":
                        set_clauses.append(f"{col} = CURRENT_TIMESTAMP")
                    else:
                        set_clauses.append(f"{col} = EXCLUDED.{col}")
                sql += f" ON CONFLICT ({conflict_col}) DO UPDATE SET {', '.join(set_clauses)}"
            else:
                sql += f" ON CONFLICT ({conflict_col}) DO NOTHING"
        return sql

    async def _flush_all(self, spider):
        """刷新所有类型的缓存"""
        for item_cls in list(self._cache.keys()):
            if self._cache.get(item_cls):
                await self._flush(item_cls, spider)