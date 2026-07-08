# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import warnings
import asyncpg
from scrapy.exceptions import ScrapyDeprecationWarning
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem
from cnblog.items import ArticleItem

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
        spider.logger.warning("🚀  CleanPipeline......................")
        adapter = ItemAdapter(item)
        # adapter.items():处理yield出来的数据；只处理传过来，需要处理的
        # adapter.field_name():以item管道定义的原始数据
        for field,value in adapter.items():
            if isinstance(value,str):
                adapter[field] = value.strip("")
        # 可以在此处加验证 或者单独一个类
        return item

class ValidatePipeline:
    """数据验证"""
    
    def process_item(self, item, spider):
        spider.logger.warning("🚀  ValidatePipeline......................")
        adapter = ItemAdapter(item)
        if not adapter.get("title"):
            raise DropItem("Missing title")
        if not adapter.get("description"):
            raise DropItem("Missing description")
        return item
    
class AsyncDataBasePipeline:
    """异步数据库管道（协程管道）"""
    # 动态映射配置
    TABLE_CONFIG = {
        ArticleItem:{
            "table":"articles",
            # 插入数据
            "columns":["title","description","url","nickname","views","content","cover_image"],
             # 冲突处理：指定唯一约束列（例如 url），若为 None 则不处理冲突
            "conflict_column": "url",
            # 冲突时更新的列（不含 created_at 等不需要更新的列）
            "update_columns": ["title", "description","nickname","views","content", "cover_image", "updated_at"],
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
        spider.logger.warning("🚀🚀🚀🚀 AsyncDataBasePipeline")
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
