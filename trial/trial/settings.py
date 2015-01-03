# -*- coding: utf-8 -*-

# Scrapy settings for trial project
#
# For simplicity, this file contains only the most important settings by
# default. All the other settings are documented here:
#
#     http://doc.scrapy.org/en/latest/topics/settings.html
#

BOT_NAME = 'trial'

LOG_FILE = 'trial.log'
LOG_LEVEL = 'DEBUG'
LOG_ENABLED = True

SPIDER_MODULES = ['trial.spiders']
NEWSPIDER_MODULE = 'trial.spiders'

ITEM_PIPELINES = {
    'trial.pipelines.JsonLocationsPipeline': 500,
}

# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = "Scrapy/0.24 (+http://scrapy.org)"
