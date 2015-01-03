import scrapy
from scrapy.http import Request
from trial.items import ProductItem

"""
Design:

* Grab every category link ('menuLink') from the start url.
* For each category link:
** Grab each product link ('item_container').
** Navigate to the next page in the category, repeat loop.
* For each product link:
** Navigate to the specific product page.
** Scrape the specific product data.

"""

class HhgreggSpider(scrapy.Spider):
    name = 'hhgregg'
    allowed_domains = ["hhgregg.com"]
    start_urls = ["http://www.hhgregg.com/"]

    def parse(self, response):
        category_links = response.xpath("//a[@class='menuLinks']/@href").extract()

        for category_link in category_links:
            product_links = self.get_product_links(category_link)

            for product_link in product_links:

                pass

                yield item

            pass

    def get_product_links(self, link):
        product_links = []

        pass

        return product_links

    def parse_product(self, response):
        pass
