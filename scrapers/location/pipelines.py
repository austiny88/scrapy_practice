# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import json

from scrapy.contrib.exporter import JsonItemExporter


class JsonLocationsPipeline(object):
    def __init__(self):
        self.files = {}
        self.exporter = None

    def process_item(self, item, spider):
        self.exporter.export_item(item)

        return item

    def open_spider(self, spider):
        file = open('apple_locations.json', 'w')
        self.files[spider] = file
        self.exporter = JsonItemExporter(file)
        self.exporter.start_exporting()

    def close_spider(self, spider):
        self.exporter.finish_exporting()
        file = self.files.pop(spider)
        file.close()