import scrapy
from scrapy.http import Request
from scrapy.selector import Selector
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

get_product_links:
- need to know how many products per page (can probably assume the default of 12)
- need to know when there are no more product pages to visit (either calculate, or look for lack of next page button)

* Build the url that will be used to fetch successive product pages
* Grab the product urls from the current page.
* Loop until there are no more products in the current category


"""

class HhgreggSpider(scrapy.Spider):
    name = 'hhgregg'
    allowed_domains = ["hhgregg.com"]
    start_urls = ["http://www.hhgregg.com/"]

    def parse(self, response):
        #all_products = []

        category_links = response.xpath("//a[@class='menuLinks']/@href").extract()

        self.log("{} Category links to visit".format(len(category_links)), level=scrapy.log.INFO)

        for category_link in category_links:
            self.log("Category link: '{}'".format(category_link), level=scrapy.log.INFO)

            yield Request(url=category_link, callback=self.handle_category)

    def handle_category(self, response):
        # The products are zero-index based, FYI
        self.log("inside get_product_links...", level=scrapy.log.DEBUG)

        category_products = []

        prod_per_page = 12

        sel = Selector(response=response)

        # Find the 'next page' url
        try:
            raw_url = sel.re("SearchBasedNavigationDisplayJS.init\('.*'")[0]
        except (ValueError, IndexError) as e:
            self.log("Could not find next product page url", level=scrapy.log.INFO)
            return

        self.log("Found next product page url", level=scrapy.log.DEBUG)

        # clean up the url
        if raw_url[-1] == u"'" or raw_url[-1] == u'\r':
            raw_url = raw_url[:-1]

        if raw_url[-1] != u'=':
            self.log("Unexpected ending char: ...'{}'".format(raw_url[-5:]), level=scrapy.log.INFO)
            # Even though we didn't get what was expected, try to proceed anyway

        url = raw_url + u'&beginIndex='

        pages = 0

        products = [product for product in self.parse_page(response)]

        category_products.extend(products)

        while len(products) >= prod_per_page:
            pages += 1

            # Build the new url:
            # split the old 'beginIndex' value off (at the first, rightmost '='), this creates a list of len == 2
            # select the first element of the list, this is the body of the url
            # add back to it the '=' and the new product 'beginIndex'
            url = url.rsplit('=', 1)[0] + u'={}'.format(prod_per_page * pages)

            page_products = Request(url=url, callback=self.parse_page)

            category_products.extend(page_products)

        return category_products

    def parse_page(self, response):
        self.log("Inside parse_page", level=scrapy.log.DEBUG)

        #page_products = []

        product_links = response.xpath("//div[@class='item_container']/div[@class='information']/h3/a/@href").extract()

        for link in product_links:
            url = "http://www.hhgregg.com" + link

            self.log("product link: {}".format(url), level=scrapy.log.DEBUG)

            yield Request(url=url, callback=self.parse_product)

    def parse_product(self, response):
        self.log("Inside parse_product", level=scrapy.log.DEBUG)

        return ProductItem()