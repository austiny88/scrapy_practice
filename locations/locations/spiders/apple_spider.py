import scrapy

from locations.items import LocationsItem

class AppleSpider(scrapy.Spider):
    name = 'apple'
    allowed_domains = ["apple.com"]
    start_urls = ["http://www.apple.com/retail/storelist/"]

    rules = (
        Rule(LinkExtractor(allow="http:\/\/www\.apple\.com\/\w*\/retail\/\w*\/"),
             'parse_location', follow=True,
             ),
    )

    def parse(self, response):
        pass

    def parse_location(self, response):
        pass