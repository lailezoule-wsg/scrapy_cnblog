# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class CnblogItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass

class ArticleItem(scrapy.Item):
    title = scrapy.Field()
    nickname = scrapy.Field()
    views = scrapy.Field()
    description = scrapy.Field()
    url = scrapy.Field()
    content = scrapy.Field()
    cover_image = scrapy.Field()
    cover_image_local = scrapy.Field()
    created_at = scrapy.Field()
    updated_at = scrapy.Field()
