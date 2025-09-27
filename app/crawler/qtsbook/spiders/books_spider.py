import re
from urllib.parse import urljoin
from datetime import datetime, timezone
import scrapy
from qtsbook.items import BookItem

BASE = "https://books.toscrape.com/"

class BooksSpider(scrapy.Spider):
    name = "books"
    allowed_domains = ["books.toscrape.com"]
    start_urls = [BASE]

    def parse(self, response):
        for href in response.css(".side_categories a::attr(href)").getall():
            href = href.strip()
            if href and "category" in href:
                yield response.follow(href, callback=self.parse_category)

    def parse_category(self, response):
        category_name = response.css(".page-header h1::text").get() or response.css("h1::text").get()

        # Product cards on the listing page
        for href in response.css("article.product_pod h3 a::attr(href)").getall():
            yield response.follow(href, callback=self.parse_detail, cb_kwargs={"category": category_name})

        # Category specific pagination
        next_rel = response.css("li.next a::attr(href)").get()
        if next_rel:
            yield response.follow(next_rel, callback=self.parse_category)

    def parse_detail(self, response, category):
        def td(label):
            xpath = f'//th[normalize-space()="{label}"]/following-sibling::td/text()'
            return response.xpath(xpath).get()

        price_excl = td("Price (excl. tax)")
        price_incl = td("Price (incl. tax)")
        tax = td("Tax")
        num_reviews = td("Number of reviews") or "0"

        rating_class = response.css("p.star-rating::attr(class)").get("")  # e.g., "star-rating Three"
        m = re.search(r"star-rating\s+(\w+)", rating_class)
        rating_name = (m.group(1) if m else "Zero").lower()
        mapping = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
        rating = mapping.get(rating_name, 0)

        availability_text = " ".join(t.strip() for t in response.css("div.product_main p.availability ::text").getall()).strip()

        item = BookItem()
        item["url"] = response.url
        item["name"] = response.css("div.product_main h1::text").get()
        item["description"] = (response.css("#product_description ~ p::text").get() or "").strip()
        item["category"] = category
        item["image_url"] = urljoin(response.url, response.css("#product_gallery img::attr(src)").get("") or "")
        item["rating"] = rating
        item["availability"] = availability_text
        item["price_excl_tax"] = price_excl
        item["price_incl_tax"] = price_incl
        item["tax"] = tax
        item["num_reviews"] = int(num_reviews) if num_reviews.isdigit() else 0

        item["source"] = "books.toscrape.com"
        item["raw_html"] = response.body
        item["crawled_at"] = datetime.now(timezone.utc)

        yield item

