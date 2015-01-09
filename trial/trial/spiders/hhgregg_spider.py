import json
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
- assume 12 products per page (hhgregg default)
- determine number of pages to visit

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

        # I don't see a distinction between between the following on hhgregg
        mpn = self.get_mpn(response)
        item['mpn'] = mpn
        item['sku'] = mpn
        item['upc'] = None
        item['model'] = mpn

        title = self.get_title(response)
        item['title'] = title

        item['brand'] = title.split(' ')[0] if title else None

        item['trail'] = self.get_trail(response)

        item['rating'] = self.get_rating(response)

        item['features'] = self.get_features(response)

        item['currency'] = 'USD'    # There are no hhgregg stores outside the U.S.

        item['retailer_id'] = self.get_retailer_id(response)

        item['description'] = self.get_description(response)

        item['current_price'] = self.get_current_price(response)

        item['original_price'] = self.get_original_price(response)

        item['specifications'] = self.get_specifications(response)

        online, in_store = self.get_availability(response)
        item['available_online'] = online
        item['available_instore'] = in_store

        #self.get_image_urls(mpn, item)
        image_request_url_base = 'http://hhgregg.scene7.com/is/image/hhgregg/'
        image_request_params = '_is?req=set,json'
        image_req_url = image_request_url_base + (mpn if mpn else '') + image_request_params

        image_req = Request(url=image_req_url, callback=self.get_image_urls_callback)
        image_req.meta['item'] = item

        yield image_req

    def get_image_urls(self, mpn, item):
        image_request_url_base = 'http://hhgregg.scene7.com/is/image/hhgregg/'
        image_request_params = '_is?req=set,json'
        image_req_url = image_request_url_base + (mpn if mpn else '') + image_request_params

        image_req = Request(url=image_req_url, callback=self.get_image_urls_callback)
        image_req.meta['item'] = item

        return image_req

    def get_image_urls_callback(self, response):
        self.log("Inside image_url callback", level=scrapy.log.DEBUG)

        item = response.meta['item']
        body = response.body    # body includes json data

        # The slice below discards non-json data at the beginning and end of the body
        image_req_dict = json.loads(body[body.index('{'):body.rindex('}')+1])
        image_data_list = image_req_dict['set']['item']

        image_urls = []
        for image_data in image_data_list:
            image_urls.append('http://hhgregg.scene7.com/is/image/' + image_data['i']['n'])

        item['image_urls'] = image_urls
        item['primary_image_url'] = image_urls[0]

        return item

    def get_mpn(self, response):
        # Ex. '(Model: WRX735SDBM)'
        try:
            raw_mpn = response.xpath("//span[@class='model_no']/text()").extract()[0]
            mpn = raw_mpn.split(':')[1].strip().strip(')')

            return mpn
        except IndexError as e:
            self.log("No mpn found", level=scrapy.log.INFO)

            return None

    def get_title(self, response):
        # Ex. 'Whirlpool 24.5 Cu. Ft. Stainless Steel French Door 4-Door Refrigerator'
        try:
            title = response.xpath("//h1[@class='catalog_link CachedItemSegmentItemDisplay']/text()").extract()[0]

            return title
        except IndexError as e:
            self.log("No title found", level=scrapy.log.INFO)

            return None

    def get_trail(self, response):
        return response.xpath("//div[@id='breadcrumb']/a/text()").extract()

    def get_rating(self, response):
        try:
            rating_str = response.xpath("//span[@class='pr-rating pr-rounded average']/text()").extract()[0]
        except IndexError as e:
            self.log("Rating, failed first attempt", level=scrapy.log.INFO)

            try:
                rating_text = response.xpath(
                        "//script[@type='text/javascript' and contains(text(), 'ratingUrl=')]"
                        ).extract()[0]
                rating_str = rating_text.split('ratingUrl=')[1].split("'")[0]
            except IndexError as e:
                self.log("Rating, failed second attempt", level=scrapy.log.INFO)

                rating_str = None

        try:
            rating = int((float(rating_str) / 5) * 100)
        except (ValueError, TypeError) as e:
            self.log("Couldn't convert rating to float: {}".format(rating_str), level=scrapy.log.INFO)

            rating = None

        return rating

    def get_features(self, response):
        """
        features = response.xpath("//div[@class='features_list']/ul/li/span/text()").extract()
        features_bold = response.xpath("//div[@class='features_list']/ul/li/span/b/text()").extract()

        if len(features_bold) == len(features):
            return [bold + feature for bold, feature in zip(features_bold, features)]

        return features
        """
        features = []
        raw_features = response.xpath("//div[@class='features_list']/ul/li")
        for line in raw_features:
            child_nodes = line.xpath(".//child::*/text()").extract()
            feature_text = ''
            for text in child_nodes:
                feature_text += text
            features.append(feature_text)

        return features


    def get_description(self, response):
        try:
            description = response.xpath("//div[@id='Features']/div[@class='']/p/text()").extract()[0]
        except IndexError as e:
            self.log("No description found", level=scrapy.log.INFO)

            description = ''

        return description

    def get_retailer_id(self, response):
        try:
            raw_id = response.xpath("//div[contains(@id, 'productIdForPartNum')]/@id").extract()[0]

            return raw_id.split('_')[1]
        except IndexError as e:
            self.log("Failed to find retailer_id", level=scrapy.log.INFO)

            return None

    def get_current_price(self, response):
        try:
            raw_current_price = response.xpath("//span[@class='price spacing']/text()").extract()[0]
            price = raw_current_price\
                    .replace('\n', '')\
                    .replace('\r', '')\
                    .replace('\t', '')\
                    .replace(' ', '')

            return price
        except IndexError as e:
            self.log("No current price found", level=scrapy.log.INFO)

            return None

    def get_original_price(self, response):
        try:
            raw_original_price = response.xpath("//div[@class='reg_price strike-through']/span[2]/text()").extract()[0]
            original_price = raw_original_price\
                    .replace('\n', '')\
                    .replace('\r', '')\
                    .replace('\t', '')\
                    .replace(' ', '')

            return original_price
        except IndexError as e:
            self.log("No original price found", level=scrapy.log.INFO)

            return None

    def get_specifications(self, response):
        specs = {}
        details = response.xpath("//div[@class='specDetails']")
        for detail in details:
            raw_spec_names = detail.xpath(".//span[@class='dotted']/text()").extract()
            raw_spec_values = detail.xpath(".//span[@class='specdesc_right']/text()").extract()

            spec_names = [name.split(':')[0] for name in raw_spec_names]
            spec_values = [value.replace('\n', '').replace('\r', '').strip().rstrip() for value in raw_spec_values]

            for spec_name, spec_value in zip(spec_names, spec_values):
                specs[spec_name] = spec_value

        return specs

    def get_availability(self, response):
        if response.xpath("//div[@class='product_details']/div[contains(text(), 'DISCONTINUED')]"):
            online, in_store = False, False
        else:
            online = False if response.xpath("//div[contains(@class, 'InstoreSpecialOrder')]") else True
            in_store = True    # Haven't been able to find an item that was online only for all locations

        return online, in_store