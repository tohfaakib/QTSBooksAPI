import os
from pathlib import Path
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRAPY_ROOT = REPO_ROOT / "app" / "crawler"

def main():
    try:
        from dotenv import load_dotenv
        load_dotenv(REPO_ROOT / ".env")
    except Exception:
        pass

    os.chdir(SCRAPY_ROOT)

    settings = get_project_settings()
    settings.set("LOG_LEVEL", os.getenv("QTS_LOG_LEVEL", "INFO"), priority="cmdline")

    resume = os.getenv("QTS_SCRAPY_RESUME", "false").lower() in {"1","true","yes","on"}
    if resume:
        jobdir = REPO_ROOT / "app" / ".job" / "books"
        jobdir.mkdir(parents=True, exist_ok=True)
        settings.set("JOBDIR", str(jobdir), priority="cmdline")

    os.environ.setdefault("QTS_MONGODB_URI", "mongodb://mongo:27017")
    os.environ.setdefault("QTS_MONGODB_DB", "qtsbook")

    from qtsbook.spiders.books_spider import BooksSpider
    process = CrawlerProcess(settings)
    process.crawl(BooksSpider)
    process.start()

if __name__ == "__main__":
    main()
