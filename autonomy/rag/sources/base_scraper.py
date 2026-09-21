import httpx
from bs4 import BeautifulSoup
from datetime import datetime

class BaseScraper:
    """
    Shared scraping logic for all UMN data sources.

    Subclasses must define SOURCE_NAME and can override
    parse_text() for site-specific HTML structures.
    
    Attributes:
        SOURCE_NAME: identifier for the data source, must be set by subclasses
    """
    
    SOURCE_NAME = None

    async def fetch_page(self, url: str) -> str:
        """
        Fetches raw HTML from the given URL.

        Args:
            url: the URL to fetch

        Returns:
            the raw HTML as a string
        """

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            return response.text


    def parse_text(self, html: str) -> str:
        """
        Strips HTML tags and returns readable text. Override for custom parsing.

        Args:
            html: the raw HTML from fetch_page

        Returns:
            returns the modified string without HTML tags, becomes readable.
        """

        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text(separator=" ", strip=True)


    async def scrape(self, urls: list[str]) -> list[dict]:
        """
        Fetches and parses a list of URLs.
        Returns a list of document dicts ready for the indexer.

        Args:
            urls: list of urls to scrape

        Returns:
            dictionary of urls
        """

        # Checks if SOURCE_NAME is defined, if not err.
        if self.SOURCE_NAME is None:
            raise NotImplementedError("Subclasses must define SOURCE_NAME")
        

        documents = []

        # try each url, some may fail
        for url in urls:
            try:
                html = await self.fetch_page(url)
                text = self.parse_text(html)
                documents.append({
                    "text": text,
                    "source_url": url,
                    "source_name": self.SOURCE_NAME,
                    "scraped_at": datetime.utcnow().isoformat()
                })

            except Exception as e:
                print(f"Skipping {url}: {e}")

        return documents
        

