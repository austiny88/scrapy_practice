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

        self.log("{} Category links to visit".format(len(category_links)), level=scrapy.log.DEBUG)

        for category_link in category_links:
            self.log("Category link: {}".format(category_link), level=scrapy.log.DEBUG)

            product_links = Request(url=category_link, callback=self.get_product_links)
            """
            for product_link in product_links:
                self.log("Product link: {}".format(product_link), level=scrapy.log.DEBUG)

                pass

                #yield item

            pass"""

    def get_product_links(self, response):

        product_links = []

        product_links.extend(
                response.xpath("//div[@class='item_container']/div[@class='information']/h3/a/@href").extract()
                )

        return product_links

    def parse_product(self, response):
        pass
