from .base_scraper import BaseScraper

# unused
class ClassInfoScraper(BaseScraper):
    """
    Scraper for UMN Course info pages from Coursedog.

    Fetches and parses course details from:
    https://umtc.catalog.prod.coursedog.com/courses/1234567

    Attributes:
        SOURCE_NAME: identifier for the data source, defined in subclass
    """

    SOURCE_NAME = "UMN Class Info"
