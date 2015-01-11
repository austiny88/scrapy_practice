import json
import math

import scrapy
from scrapy.http import Request
from scrapy.selector import Selector
from trial.items import ProductItem


# The default number of products per page on hhgregg
PRODUCTS_PER_PAGE = 12


class HhgreggSpider(scrapy.Spider):
    name = 'hhgregg'
    allowed_domains = ["hhgregg.com", "scene7.com"]
    start_urls = ["http://www.hhgregg.com/"]

    def parse(self, response):
        category_links = response.xpath("//a[@class='menuLinks']/@href").extract()

        self.log("{} Category links to visit".format(len(category_links)), level=scrapy.log.INFO)

        for category_link in category_links:
            self.log("Category link: '{}'".format(category_link), level=scrapy.log.INFO)
            yield Request(url=category_link, callback=self.handle_category)

    def handle_category(self, response):
        # The products are zero-index based, FYI

        category_products = []

        sel = Selector(response=response)

        # Find the 'next page' url
        try:
            re_result = sel.re("SearchBasedNavigationDisplayJS.init\('.*'")[0]
        except (ValueError, IndexError) as e:
            self.log(
                    "Could not find next product page url, currently on: '{}'".format(response.url),
                    level=scrapy.log.INFO
                    )
            return

        # Clean up the url
        try:
            raw_url = re_result.rsplit("('")[1]
        except IndexError as e:
            self.log("Failed to split regex result: {}".format(re_result), level=scrapy.log.ERROR)
            return

        if raw_url[-1] == "'" or raw_url[-1] == '\r':
            raw_url = raw_url[:-1]

        if raw_url[-1] != '=':
            self.log("Unexpected ending char: ...'{}'".format(raw_url[-5:]), level=scrapy.log.INFO)
            # Even though we didn't get what was expected, try to proceed anyway

        url = raw_url + '&beginIndex='

        # Find the number of pages to visit
        total_pages = self.calculate_total_pages(response)

        self.log("In category, {} pages".format(total_pages), level=scrapy.log.DEBUG)

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
            url = url.rsplit('=', 1)[0] + '={}'.format(PRODUCTS_PER_PAGE * pages)

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

        identifiers = self.get_identifiers(response)

        if not identifiers:
            # If get_identifiers return 'None', then there isn't a product to scrape
            self.log("No products to scrape on this page", level=scrapy.log.INFO)
            return

        item['mpn'] = identifiers['mpn']
        item['sku'] = identifiers['sku']
        item['upc'] = identifiers['upc']
        item['model'] = identifiers['model']
        item['retailer_id'] = identifiers['retailer_id']

        title = self.get_title(response)
        item['title'] = title
        item['brand'] = title.split(' ')[0] if title else None

        item['trail'] = self.get_trail(response)
        item['rating'] = self.get_rating(response)
        item['features'] = self.get_features(response)
        item['currency'] = 'USD'    # There are no hhgregg stores outside the U.S.
        item['description'] = self.get_description(response)
        item['current_price'] = self.get_current_price(response)
        item['original_price'] = self.get_original_price(response)
        item['specifications'] = self.get_specifications(response)

        online, in_store = self.get_availability(response)
        item['available_online'] = online
        item['available_instore'] = in_store

        image_req = self.get_image_urls(item['mpn'], item)
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
        item = response.meta['item']
        body = response.body    # body includes json data

        # The slice below discards non-json data at the beginning and end of the body
        image_req_dict = json.loads(body[body.index('{'):body.rindex('}')+1])
        try:
            image_data = image_req_dict['set']['item']
        except KeyError as e:
            self.log("Failure to get image_data_list: image_req_dict: {}".format(image_req_dict), level=scrapy.log.INFO)

            item['image_urls'] = None
            item['primary_image_url'] = None

            return item

        image_urls = []
        if isinstance(image_data, list):
            for data in image_data:
                try:
                    image_urls.append('http://hhgregg.scene7.com/is/image/' + data['i']['n'])
                except TypeError as e:
                    self.log("Image failure in list, image_req_dict: {}".format(image_req_dict), level=scrapy.log.INFO)
        elif isinstance(image_data, dict):
            try:
                image_urls.append('http://hhgregg.scene7.com/is/image/' + image_data['i']['n'])
            except TypeError as e:
                self.log("Image failure in dict, image_req_dict: {}".format(image_req_dict), level=scrapy.log.INFO)
        else:
            self.log("Unaccounted for image_data type: {}".format(type(image_data)), level=scrapy.log.INFO)

        item['image_urls'] = image_urls if image_urls else None
        item['primary_image_url'] = image_urls[0] if len(image_urls) > 0 else None

        return item

    def calculate_total_pages(self, response):
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
        total_pages = int(math.ceil(num_products / PRODUCTS_PER_PAGE))

        return total_pages

    def get_identifiers(self, response):
        identifiers = {}

        try:
            sel = response.xpath("//div[@class='product_visual']/script[contains(text(), 'mboxCreate')]")[0]
        except IndexError as e:
            self.log("This page '{}', doesn't seem to have a product".format(response.url), level=scrapy.log.INFO)
            return None

        try:
            mpn = sel.re("entity\.id=(.*?)'")[0]
        except IndexError as e:
            self.log("Could not find mpn", level=scrapy.log.INFO)
            mpn = None

        try:
            retailer_id = sel.re("entity\.message=(.*?)'")[0]
        except IndexError as e:
            self.log("Could not find retailer_id", level=scrapy.log.INFO)
            retailer_id = None

        sku = None
        upc = None
        model = mpn

        identifiers['mpn'] = mpn
        identifiers['sku'] = sku
        identifiers['upc'] = upc
        identifiers['model'] = model
        identifiers['retailer_id'] = retailer_id

        return identifiers

    def get_title(self, response):
        # Ex. 'Whirlpool 24.5 Cu. Ft. Stainless Steel French Door 4-Door Refrigerator'
        try:
            title = response.xpath(
                    "//div[@id='prod_detail_main']/h1[contains(@class, 'catalog_link')]/text()"
                    ).extract()[0]
        except IndexError as e:
            self.log("No title found", level=scrapy.log.INFO)
            title = None

        return title

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
            description = None

        return description

    def get_current_price(self, response):
        try:
            raw_current_price = response.xpath("//span[@class='price spacing']/text()").extract()[0]
            price = raw_current_price\
                    .replace('\n', '')\
                    .replace('\r', '')\
                    .replace('\t', '')\
                    .replace(' ', '')
        except IndexError as e:
            self.log("No current price found", level=scrapy.log.INFO)
            price = None

        return price

    def get_original_price(self, response):
        try:
            raw_original_price = response.xpath("//div[@class='reg_price strike-through']/span[2]/text()").extract()[0]
            original_price = raw_original_price\
                    .replace('\n', '')\
                    .replace('\r', '')\
                    .replace('\t', '')\
                    .replace(' ', '')
        except IndexError as e:
            self.log("No original price found", level=scrapy.log.INFO)
            original_price = None

        return original_price

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