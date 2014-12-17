import scrapy
from scrapy.http import Request
from location.items import LocationItem


class AppleSpider(scrapy.Spider):
    name = 'apple'
    allowed_domains = ["apple.com"]
    start_urls = ["http://www.apple.com/retail/storelist/"]

    def parse(self, response):
        raw_store_links = response.selector.xpath("//div[@id='content']").xpath(".//li").xpath(".//a")

        location_items = []
        for path in raw_store_links:
            href = path.xpath("@href").extract()[0]
            url = u"http://www.apple.com" + href
            location_item = Request(url=url, callback=parse_store)
            location_items.append(location_item)

        return location_items

    def parse_store(self, response):
        pass