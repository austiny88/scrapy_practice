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
            #print(url)
            location_item = Request(url=url, callback=parse_store)
            location_items.append(location_item)

        return location_items

    def parse_store(self, response):
        item = LocationItem()

        country_abrev = response.url.split('http://www.apple.com/')[1].split('/')
        if country_abrev == 'retail':
            country_abrev = 'us'
        item['country'] = country_abrev

        item['city'] = response.xpath("//div[@id='gallery-mapSwap']/div[1]//span[@class='locality']/text()").extract()[0]
        item['state'] = response.xpath("//div[@id='gallery-mapSwap']/div[1]//span[@class='region']/text()").extract()[0]

        raw_street_addresses = response.xpath("//div[@id='gallery-mapSwap']/div[1]//div[@class='street-address']/text()").extract()
        street_address = []
        for raw_street_address in raw_street_addresses:
            street_address.append(raw_street_address.replace('\n').replace('\t'))

        item['address'] = street_address
        item['zipcode'] = response.xpath("//div[@id='gallery-mapSwap']/div[1]//span[@class='postal-code']/text()").extract()[0]
        item['hours'] =
        item['services'] =
        item['store_email'] =
        item['phone_number'] =
        item['store_id'] =
        item['store_url'] =
        item['store_name'] =
        item['weekly_ad_url'] =
        item['store_image_url'] =
        item['store_floor_plan_url'] =