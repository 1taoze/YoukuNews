# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

from pymongo import MongoClient
from scrapy import Request
from scrapy.pipelines.images import ImagesPipeline
from scrapy.pipelines.files import FilesPipeline


# https://docs.scrapy.org/en/latest/topics/item-pipeline.html#write-items-to-mongodb
# The main point of this example is to show how to use from_crawler() method \
# and how to clean up the resources properly.
class VideoInfoPipeline(object):
    collection_name = 'VideoInfo'

    def __init__(self, mongo_uri, mongo_db):
        self.mongo_uri = mongo_uri  # 统一资源标识符
        self.mongo_db = mongo_db  # 数据库名称

    @classmethod
    def from_crawler(cls, crawler):
        return cls(mongo_uri=crawler.settings.get('MONGO_URI'),
                   mongo_db=crawler.settings.get('MONGO_DB', 'items'))

    def open_spider(self, spider):
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        # 对集合(collection)插入一个文档(document)
        self.db[self.collection_name].insert_one(dict(item))
        return item


# https://doc.scrapy.org/en/latest/topics/media-pipeline.html#module-scrapy.pipelines.files
class VideoThumbPipeline(ImagesPipeline):
    # 从item中取出缩略图的url并下载文件
    def get_media_requests(self, item, info):
        yield Request(url=item['thumb_url'], meta={'item': item})

    # 自定义缩略图路径(及命名), 注意该路径是 IMAGES_STORE 的相对路径
    def file_path(self, request, response=None, info=None):
        vid = request.meta['item']['vid']  # 获取item的vid
        return "%s/thumb.jpg" % vid  # 返回路径及命名格式

    # 下载完成后, 将缩略图本地路径(IMAGES_STORE + 相对路径)填入到 item 的 thumb_path
    def item_completed(self, results, item, info):
        item['thumb_path'] = self.store.basedir + [x['path'] for ok, x in results if ok][0]
        return item


# https://doc.scrapy.org/en/latest/topics/media-pipeline.html#module-scrapy.pipelines.files
class VideoFilesPipeline(FilesPipeline):
    # 从item中取出分段视频的url列表并下载文件
    def get_media_requests(self, item, info):
        urls = item['file_urls']
        for url in urls:
            yield Request(url=url, meta={'item': item, 'index': urls.index(url)})

    # 自定义分段视频下载到本地的路径(以及命名), 注意该路径是 FILES_STORE 的相对路径
    def file_path(self, request, response=None, info=None):
        vid = request.meta['item']['vid']  # 获取item的vid
        index = request.meta['index']  # 获取当前分段文件序号
        return "%s/%s.mp4" % (vid, index)  # 返回路径及命名格式

    # 下载完成后, 将分段视频本地路径列表(FILES_STORE + 相对路径)填入到 item 的 file_paths
    def item_completed(self, results, item, info):
        item['file_paths'] = [self.store.basedir + x['path'] for ok, x in results if ok]
        return item
