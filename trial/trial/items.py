# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class LocationItem(scrapy.Item):
    city = scrapy.Field()
    hours = scrapy.Field()
    state = scrapy.Field()
    country = scrapy.Field()
    address = scrapy.Field()
    zipcode = scrapy.Field()
    services = scrapy.Field()
    store_id = scrapy.Field()
    store_url = scrapy.Field()
    store_name = scrapy.Field()
    store_email = scrapy.Field()
    phone_number = scrapy.Field()
    weekly_ad_url = scrapy.Field()
    store_image_url = scrapy.Field()
    store_floor_plan_url = scrapy.Field()


class ProductItem(scrapy.Item):
    mpn = scrapy.Field()
    sku = scrapy.Field()
    upc = scrapy.Field()
    brand = scrapy.Field()
    title = scrapy.Field()
    trail = scrapy.Field()
    model = scrapy.Field()
    rating = scrapy.Field()
    currency = scrapy.Field()
    features = scrapy.Field()
    image_urls = scrapy.Field()
    retailer_id = scrapy.Field()
    description = scrapy.Field()
    current_price = scrapy.Field()
    original_price = scrapy.Field()
    specifications = scrapy.Field()
    available_online = scrapy.Field()
    available_instore = scrapy.Field()
    primary_image_url = scrapy.Field()