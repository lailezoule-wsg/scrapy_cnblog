from itemloaders import ItemLoader
from itemloaders.processors import TakeFirst, MapCompose, Join
from datetime import datetime
import pytz
from cnblog.items import ArticleItem


def strip_text(text):
    """去除首尾空白"""
    return text.strip() if isinstance(text, str) else text


def parse_datetime(text):
    """将字符串解析为带时区的 datetime"""
    if not text:
        return None
    try:
        dt = datetime.strptime(text.strip(), '%Y-%m-%d %H:%M')
        return pytz.timezone('Asia/Shanghai').localize(dt)
    except (ValueError, AttributeError):
        return None


def normalize_image_url(url):
    """处理协议相对 URL"""
    if url and url.startswith('//'):
        return 'https:' + url
    return url


class ArticleLoader(ItemLoader):
    default_item_class = ArticleItem
    default_input_processor = MapCompose(strip_text)
    default_output_processor = TakeFirst()

    # 特殊字段单独配置
    cover_image_in = MapCompose(strip_text, normalize_image_url)

    created_at_in = MapCompose(strip_text, parse_datetime)
    created_at_out = TakeFirst()

    updated_at_in = MapCompose(strip_text, parse_datetime)
    updated_at_out = TakeFirst()

    views_in = MapCompose(lambda x: int(x) if x and x.isdigit() else 0)
    views_out = TakeFirst()