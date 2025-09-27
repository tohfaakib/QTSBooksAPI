# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import gzip
import hashlib
from datetime import datetime, timezone
from pymongo import MongoClient
from scrapy.utils.project import get_project_settings
import re

PRICE_RE = re.compile(r"[\d.]+")

def parse_price_num(s: str | None) -> float | None:
    if not s:
        return None
    m = PRICE_RE.search(s)
    return float(m.group(0)) if m else None

class MongoPipeline:
    def __init__(self):
        self.client = None
        self.db = None
        self.books = None
        self.changes = None

    def open_spider(self, spider):
        s = get_project_settings()
        self.client = MongoClient(s.get("MONGODB_URI"))
        self.db = self.client[s.get("MONGODB_DB")]
        self.books = self.db["books"]
        self.changes = self.db["changes"]

        # indexes for uniqueness & fast API queries
        self.books.create_index("url", unique=True)
        self.books.create_index([("category", 1), ("price_incl_tax", 1), ("rating", -1)])

    def close_spider(self, spider):
        if self.client:
            self.client.close()

    def process_item(self, item, spider):
        item["price_incl_tax_num"] = parse_price_num(item.get("price_incl_tax"))
        item["price_excl_tax_num"] = parse_price_num(item.get("price_excl_tax"))

        key = (
            f"{item.get('name','')}"
            f"{item.get('price_incl_tax','')}"
            f"{item.get('availability','')}"
            f"{item.get('rating','')}"
            f"{item.get('num_reviews','')}"
        ).encode("utf-8", "ignore")

        item["content_hash"] = hashlib.sha1(key).hexdigest()
        item["crawled_at"] = datetime.utcnow()

        if "raw_html" in item:
            item["raw_html_gz"] = gzip.compress(item.pop("raw_html"))

        prev = self.books.find_one({"url": item["url"]}, {"content_hash": 1})

        doc = dict(item)
        self.books.update_one({"url": item["url"]}, {"$set": doc}, upsert=True)

        if prev and prev.get("content_hash") != item["content_hash"]:
            self.changes.insert_one({
                "url": item["url"],
                "changed_at": datetime.now(timezone.utc),
                "prev_hash": prev.get("content_hash"),
                "new_hash": item["content_hash"],
                "fields_hint": ["name","price_incl_tax","availability","rating","num_reviews"],
            })

        return item
