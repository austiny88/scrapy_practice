import scrapy
from scrapy.http import Request
from trial.items import LocationItem


class WetsealSpider(scrapy.Spider):
    name = 'wetseal'
    allowed_domains = ["wetseal.com"]
    start_urls = ["http://www.wetseal.com/Stores"]

    def parse(self, response):
        search_url = response.xpath("//*[@id='dwfrm_storelocator_state']/@action").extract()[0]

        state_field = response.xpath("//*[@id='dwfrm_storelocator_address_states_stateUSCA']/@id").extract()[0]

        search_field = response.xpath("//*[@id='dwfrm_storelocator_state']/fieldset/button/@name").extract()[0]
        search_value = response.xpath("//*[@id='dwfrm_storelocator_state']/fieldset/button/@value").extract()[0]
        search_field_and_value = search_field + '=' + search_value

        states = response.xpath("//*[@id='dwfrm_storelocator_address_states_stateUSCA']/option/@value").extract()
        states = [state for state in states if state != '']

        for state in states:
            url = search_url + '&' + state_field + '=' + state + '&' + search_field_and_value

            location_item = Request(url=url, method='GET', callback=self.parse_store)

            yield location_item

    def parse_store(self, response):
        self.log(response.status, level=scrapy.log.DEBUG)

        stores = response.xpath("//*[@id='store-location-results']/tbody/tr")

        for store in stores:
            item = LocationItem()

            raw_address = store.xpath(".//td[@class='store-address']/text()").extract()
            address = [line.strip().replace('\n', '').replace('\t', '') for line in raw_address]

            state_and_zip = address[1].split(', ')[1].split(' ')

            item['city'] = address[1].split(',')[0]
            item['state'] = state_and_zip[0]
            item['country'] = 'USA'    # If you count Puerto Rico, all stores are in the US
            item['address'] = address

            if len(state_and_zip) == 2:
                item['zipcode'] = state_and_zip[1]
            else:
                item['zipcode'] = None

            item['services'] = None

            item['store_email'] = None
            item['phone_number'] = item['address'][2]

            item['store_id'] = store.xpath(".//a/@id").extract()[0]
            item['store_url'] = "http://www.wetseal.com" + store.xpath(".//a/@href").extract()[0]
            item['store_name'] = store.xpath(".//div[@class='store-name']/text()")\
                    .extract()[0]\
                    .replace('\n', '')\
                    .replace('\t', '')\
                    .replace('\r', '')

            item['weekly_ad_url'] = None
            item['store_image_url'] = None
            item['store_floor_plan_url'] = None

            raw_hours = store.xpath(".//div[@class='store-hours']/text()").extract()
            item['hours'] = self.parse_to_hours_dict(raw_hours, item['store_name'])

            yield item

    def parse_to_hours_dict(self, store_hours, info):
        self.log('-- parsing hours for {}'.format(info), level=scrapy.log.DEBUG)

        # Sunday occurs twice
        days_of_week = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        days_of_week_alt = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
        operating_hours = {}

        for row in store_hours:
            hours_data = row.replace('\n', '').replace('\t', '').replace('\r', '')

            self.log("hours_data: {}".format(hours_data), level=scrapy.log.DEBUG)

            # split into days data and hours data
            try:
                raw_days_data, raw_times_data = hours_data.split(':', 1)
                self.log(
                        "unparsed days and times data: {}, {}".format(raw_days_data, raw_times_data),
                        level=scrapy.log.DEBUG
                        )
            except (ValueError, IndexError) as e:
                self.log("** failed to split into days and times data", level=scrapy.log.DEBUG)
                continue

            # handle contiguous days
            temp_days = []
            days_set = [day.strip() for day in raw_days_data.split('-')]

            self.log("days_set: {}".format(days_set), level=scrapy.log.DEBUG)

            if len(days_set) == 1:
                temp_days.append(str(days_set[0]))
            elif len(days_set) == 2:
                try:
                    first_day = days_of_week.index(days_set[0])
                except ValueError as e:
                    try:
                        first_day = days_of_week_alt.index(days_set[0])
                    except ValueError as e:
                        self.log("{} was not identified as a day of the week.".format(days_set[0]), level=scrapy.log.INFO)
                        continue

                temp_week = [days_of_week[i % 7] for i in xrange(first_day, first_day + 7)]

                try:
                    end_index = temp_week.index(days_set[1])
                except ValueError as e:
                    temp_week_alt = [days_of_week_alt[i % 7] for i in xrange(first_day, first_day + 7)]
                    try:
                        end_index = temp_week_alt.index(days_set[1])
                    except ValueError as e:
                        self.log("{} was not identified as a day of the week.".format(days_set[1]), level=scrapy.log.INFO)
                        continue

                temp_days.extend(temp_week[:end_index + 1])
            else:
                self.log("Error: days_set shouldn't be longer than 2", level=scrapy.log.INFO)

            # split hours into open and close if possible
            hours = [time.strip() for time in raw_times_data.split('-', 1)]
            open_hour = hours[0]
            if len(hours) == 1:
                close_hour = hours[0]
            else:
                close_hour = hours[1]

            self.log("open: {}, close: {}".format(open_hour, close_hour), level=scrapy.log.DEBUG)

            # apply hours to operating days
            for day in temp_days:
                operating_hours[day] = {'open': open_hour, 'close': close_hour}

        return operating_hours