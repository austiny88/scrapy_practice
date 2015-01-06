import math

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
- need to know how many pages to visit

* Build the url that will be used to fetch successive product pages
* Grab the product urls from the current page.
* Loop until there are no more products in the current category

"""


class HhgreggSpider(scrapy.Spider):
    name = 'hhgregg'
    allowed_domains = ["hhgregg.com"]
    start_urls = ["http://www.hhgregg.com/"]

    def parse(self, response):
        category_links = response.xpath("//a[@class='menuLinks']/@href").extract()

        self.log("{} Category links to visit".format(len(category_links)), level=scrapy.log.INFO)

        for category_link in category_links:
            self.log("Category link: '{}'".format(category_link), level=scrapy.log.INFO)

            yield Request(url=category_link, callback=self.handle_category)

    def handle_category(self, response):
        # The products are zero-index based, FYI

        prod_per_page = 12
        category_products = []

        sel = Selector(response=response)

        # Find the 'next page' url
        try:
            re_result = sel.re("SearchBasedNavigationDisplayJS.init\('.*'")[0]
            self.log("Found next product page url", level=scrapy.log.DEBUG)
        except (ValueError, IndexError) as e:
            self.log("Could not find next product page url", level=scrapy.log.DEBUG)
            return

        # Clean up the url
        try:
            raw_url = re_result.rsplit("('")[1]
        except IndexError as e:
            self.log("Failed to split regex result: {}".format(re_result), level=scrapy.log.ERROR)
            return

        if raw_url[-1] == u"'" or raw_url[-1] == u'\r':
            raw_url = raw_url[:-1]

        if raw_url[-1] != u'=':
            self.log("Unexpected ending char: ...'{}'".format(raw_url[-5:]), level=scrapy.log.INFO)
            # Even though we didn't get what was expected, try to proceed anyway

        url = raw_url + u'&beginIndex='

        # Calculate how many pages to visit
        # find the number products in this category
        raw_num_and_results_str = response.xpath("//div[@class='showing_prod']/text()").extract()[0]
        raw_num_str = raw_num_and_results_str.split(u'\xa0')[0]
        num_products_str = raw_num_str\
                .replace('\r', '')\
                .replace('\n', '')\
                .replace('\t', '')\
                .strip()
        num_products = float(num_products_str)
        total_pages = int(math.ceil(num_products / prod_per_page))

        self.log("In category, {} products, {} pages".format(num_products_str, total_pages), level=scrapy.log.DEBUG)

        # Parse the 1st (current) page of products
        page_products = self.parse_page(response)
        category_products.extend(page_products)
        pages = 1

        # Loop over each page of products for this category
        while pages < total_pages:
            # Build the new url:
            # split the old 'beginIndex' value off (at the first, rightmost '='), this creates a list of len == 2
            # select the first element (zeroth position) of the list, this is the body of the url
            # add back to it the '=' and the new product 'beginIndex' value
            url = url.rsplit('=', 1)[0] + u'={}'.format(prod_per_page * pages)

            page_products = Request(url=url, callback=self.parse_page)

            try:
                # If page_products is returned as iterable
                category_products.extend(page_products)
            except TypeError as e:
                # If page_products is returned as Request object
                category_products.append(page_products)

            pages += 1

        self.log("Received {} products".format(len(category_products)), level=scrapy.log.DEBUG)

        return category_products

    def parse_page(self, response):
        page_products = []

        product_links = response.xpath("//div[@class='item_container']/div[@class='information']/h3/a/@href").extract()

        for link in product_links:
            url = "http://www.hhgregg.com" + link

            self.log("product link: '{}'".format(url), level=scrapy.log.DEBUG)

            page_products.append(Request(url=url, callback=self.parse_product))

        self.log("In parse_page, found {} products".format(len(page_products)), level=scrapy.log.DEBUG)

        return page_products

    def parse_product(self, response):
        item = ProductItem()
        item['title'] = response.url

        return item