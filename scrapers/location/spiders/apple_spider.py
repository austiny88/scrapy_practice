import scrapy
from scrapy import log
from scrapy.http import Request
from location.items import LocationItem

#log.start(loglevel=log.INFO)


class AppleSpider(scrapy.Spider):
    name = 'apple'
    allowed_domains = ["apple.com"]
    start_urls = ["http://www.apple.com/retail/storelist/"]

    def parse(self, response):
        raw_store_links = response.selector.xpath("//div[@id='content']").xpath(".//li").xpath(".//a")

        #location_items = []
        for path in raw_store_links:
            href = path.xpath("@href").extract()[0]
            url = u"http://www.apple.com" + href

            location_item = Request(url=url, callback=self.parse_store)

            yield location_item

    def parse_store(self, response):
        item = LocationItem()

        split_url = response.url.split('http://www.apple.com/')[1].split('/')
        if split_url[0] == 'retail':
            country_abrev = 'us'
        else:
            country_abrev = split_url[0]
        item['country'] = country_abrev

        try:
            item['city'] = response.xpath("//span[@class='locality']/text()").extract()[0]
        except IndexError as e:
            item['city'] = None

        try:
            item['state'] = response.xpath("//span[@class='region']/text()").extract()[0]
        except IndexError as e:
            item['state'] = None

        try:
            item['zipcode'] = response.xpath("//span[@class='postal-code']/text()").extract()[0]
        except IndexError as e:
            item['zipcode'] = None

        raw_street_addresses = response.xpath("//div[@id='gallery-mapSwap']/div[1]//div[@class='street-address']/text()").extract()
        street_address = []
        for raw_street_address in raw_street_addresses:
            street_address.append(raw_street_address.replace('\n', '').replace('\t', ''))

        item['address'] = street_address

        item['hours'] = self.parse_to_hours_dict(response.xpath("//table[@class='store-info']/tr").extract())
        item['services'] = response.xpath("//*[@id='main']/header/nav[1]/div[2]/a/img/@alt").extract()
        item['store_email'] = None
        item['phone_number'] = response.xpath("//div[@class='telephone-number']/text()")\
                .extract()[0]\
                .replace('\n', '')\
                .replace('\t', '')

        item['store_id'] = None
        item['store_url'] = response.url
        item['store_name'] = response.xpath("//div[@class='store-name']/text()")\
                .extract()[0]\
                .replace('\n', '')\
                .replace('\t', '')

        item['weekly_ad_url'] = None
        item['store_image_url'] = response.xpath("//div[@class='column last']/img/@src").extract()[0]
        item['store_floor_plan_url'] = None

        return item

    def parse_to_hours_dict(self, store_hours):
        days_of_week = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
        operating_hours = {}

        for row in store_hours:
            hours_data = row\
                    .replace(' ', '')\
                    .replace('\n', '')\
                    .replace('\t', '')\
                    .replace('<tr>', '')\
                    .replace('<td>', '')\
                    .replace('</tr>', '')\
                    .replace('</td>', '')\
                    .split(':', 1)

            for data in hours_data:
                try:
                    open_hour, close_hour = data[1].split('-')
                    print('open: {}, close: {}'.format(open_hour, close_hour))#, level=log.INFO)
                except (ValueError, IndexError) as e:
                    # failed to split to open_hour and close_hour
                    # must not be a row containing useful operating hours information
                    continue

                temp_days = []
                non_parsed_days = data[0]
                days_set = non_parsed_days.split(',')
                for days_subset in days_set:
                    try:
                        contiguous_start, contiguous_end = days_subset.split('-')
                        print('cont_start: {}, cont_end: {}'.format(contiguous_start, contiguous_end))#, level=log.INFO)
                    except ValueError as e:
                        # this days_subset does not contain contiguous days (days separated by '-')
                        if days_subset in days_of_week:
                            temp_days.append(days_subset)
                        else:
                            continue
                    try:
                        start_index = days_of_week.index(contiguous_start)
                        end_index = days_of_week.index(contiguous_end)
                    except ValueError as e:
                        # contiguous_start or contiguous_end was not contained in days_of_week
                        # this row must not contain useful operating hours information
                        continue

                    temp_days.extend(days_of_week[start_index:end_index + 1])
                    print('operating_days: {}'.format(temp_days))#, level=log.INFO)

                for day in temp_days:
                    operating_hours[day] = {'open': open_hour, 'close': close_hour}

        return operating_hours