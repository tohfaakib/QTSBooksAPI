# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class BookItem(scrapy.Item):
    url = scrapy.Field()
    name = scrapy.Field()
    description = scrapy.Field()
    category = scrapy.Field()
    image_url = scrapy.Field()
    rating = scrapy.Field()
    availability = scrapy.Field()
    price_excl_tax = scrapy.Field()
    price_incl_tax = scrapy.Field()
    tax = scrapy.Field()
    num_reviews = scrapy.Field()
    crawled_at = scrapy.Field()
    source = scrapy.Field()
    raw_html = scrapy.Field()
    raw_html_gz = scrapy.Field()
    content_hash = scrapy.Field()
