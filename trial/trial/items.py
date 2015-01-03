# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class LocationItem(scrapy.Item):
    city = scrapy.Field()
    state = scrapy.Field()
    country = scrapy.Field()
    address = scrapy.Field()
    zipcode = scrapy.Field()

    hours = scrapy.Field()
    services = scrapy.Field()

    store_email = scrapy.Field()
    phone_number = scrapy.Field()

    store_id = scrapy.Field()
    store_url = scrapy.Field()
    store_name = scrapy.Field()
    weekly_ad_url = scrapy.Field()
    store_image_url = scrapy.Field()
    store_floor_plan_url = scrapy.Field()
