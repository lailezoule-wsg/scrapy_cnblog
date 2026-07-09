import json
import random
import logging
import redis.asyncio as redis
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


class AsyncCookieManager:
    """Redis-based Cookie池管理器"""
    
    def __init__(
        self,
        redis_host: str = 'localhost',
        redis_port: int = 6379,
        redis_db: int = 0,
        redis_password: Optional[str] = None,
        key_prefix: str = 'cookies:'
    ):
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            protocol=2,
            decode_responses=True  # 自动解码为字符串
        )
        self.key_prefix = key_prefix

    async def _get_key(self, spider_name: str, account: str) -> str:
        """生成Redis键名"""
        return f"{self.key_prefix}{spider_name}:{account}"

    async def get_all_cookies(self, spider_name: str) -> List[Dict[str, str]]:
        """获取某个爬虫所有的Cookie"""
        pattern = f"{self.key_prefix}{spider_name}:*"
        keys = await self.redis_client.keys(pattern)
        cookies = []
        for key in keys:
            cookie_str = await self.redis_client.get(key)
            if cookie_str:
                try:
                    cookies.append(json.loads(cookie_str))
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode cookie for key: {key}")
        return cookies

    async def get_all_cookies2(self,spider_name:str):
        pattern = f"{self.key_prefix}{spider_name}:*"
        cursor = 0
        cookies = []
        
        while True:
            # SCAN 每次返回 (新游标, [key1, key2, ...])
            cursor, keys = await self.redis_client.scan(cursor, match=pattern, count=1000)  # count 可调
            if not keys:
                # 如果本次没有返回任何 key，仍需检查游标是否为0，但通常游标为0才终止
                pass
            if keys:
                # 批量获取值
                values = await self.redis_client.mget(*keys)
                for key, cookie_str in zip(keys, values):
                    if cookie_str:
                        try:
                            cookies.append(json.loads(cookie_str))
                        except json.JSONDecodeError:
                            logger.error(f"Failed to decode cookie for key: {key}")
             # 游标为0表示迭代结束
            if cursor == 0:
                break
        return cookies
    
    # 数据量极大，可以改为生成器分批返回，避免内存暴涨;
    # 调用时使用 for cookie in iter_all_cookies(spider_name): 即可逐个处理，内存友好
    async def iter_all_cookies(self,spider_name:str):
        pattern = f"{self.key_prefix}{spider_name}:*"
        cursor = 0
        while True:
            cursor, keys = await self.redis_client.scan(cursor, match=pattern, count=1000)
            if keys:
                values = await self.redis_client.mget(*keys)
                for key, cookie_str in zip(keys, values):
                    if cookie_str:
                        try:
                            yield json.loads(cookie_str)
                        except json.JSONDecodeError:
                            logger.error(f"Failed to decode cookie for key: {key}")
            if cursor == 0:
                break

    async def get_random_cookie(self, spider_name: str) -> Optional[Dict[str, str]]:
        """随机获取一个Cookie"""
        cookies = await self.get_all_cookies(spider_name)
        if not cookies:
            return None
        return random.choice(cookies)

    async def get_cookie_by_account(self, spider_name: str, account: str) -> Optional[Dict[str, str]]:
        """根据账号获取Cookie"""
        key = await self._get_key(spider_name, account)
        cookie_str = await self.redis_client.get(key)
        if cookie_str:
            try:
                return json.loads(cookie_str)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode cookie for key: {key}")
        return None

    async def add_cookie(self, spider_name: str, account: str, cookie_dict: Dict[str, str]) -> bool:
        """添加或更新一个Cookie"""
        key = await self._get_key(spider_name, account)
        try:
            await self.redis_client.set(key, json.dumps(cookie_dict))
            logger.info(f"Cookie added/updated for account: {account}")
            return True
        except Exception as e:
            logger.error(f"Failed to save cookie for {account}: {e}")
            return False

    async def remove_cookie(self, spider_name: str, account: str) -> bool:
        """移除一个失效的Cookie"""
        key = await self._get_key(spider_name, account)
        result = await self.redis_client.delete(key)
        if result:
            logger.warning(f"Cookie removed for account: {account}")
        return bool(result)

    async def is_cookie_valid(self, spider_name: str, account: str) -> bool:
        """检查Cookie是否存在"""
        key = await self._get_key(spider_name, account)
        return await self.redis_client.exists(key) == 1

    async def get_cookie_count(self, spider_name: str) -> int:
        """获取池中Cookie数量"""
        pattern = f"{self.key_prefix}{spider_name}:*"
        return len(await self.redis_client.keys(pattern))