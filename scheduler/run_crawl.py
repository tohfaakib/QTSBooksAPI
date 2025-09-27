import os
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRAPY_ROOT = os.path.join(REPO_ROOT, "app", "crawler")
os.chdir(SCRAPY_ROOT)

def main():
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(REPO_ROOT, ".env"))
    except Exception:
        pass

    settings = get_project_settings()
    process = CrawlerProcess(settings)
    from qtsbook.spiders.books_spider import BooksSpider
    process.crawl(BooksSpider)
    process.start()

if __name__ == "__main__":
    main()
