import csv
import datetime

def load_csv_catalog(path: str) -> list[dict]:
    """
    Loads and parses the UMN Course Catalog from a locally downloaded Coursedog CSV file.

    Scrapes provided CSV file from:
    https://umtc.catalog.prod.coursedog.com/courses

    Args:
        path: the location of the CSV file

    Returns:
        a list of document dicts, each with keys: text, source_url, source_name, scraped_at.
        Rows with empty descriptions are skipped.
    """
    
    with open(path, "r") as file:
        reader = csv.DictReader(f=file)

        documents = []
        for row in reader:
            if not row['Course description'].strip():
                continue

            text = (
                f"{row['Course subject code']} {row['Course number']} - {row['Course name']}\n"
                f"Description: {row['Course description']}\n"
                f"Minimum Credits: {row['Minimum credits']}\n"
                f"Maximum Credits: {row['Maximum credits']}\n"
                f"Requirements: {row['Requirements']}\n"
                f"Typically Offered: {row['Typically offered term(s)']}"
            )

            documents.append({
                "text": text,
                "source_url": f"catalog:{row['Course subject code']}{row['Course number']}",
                "source_name": "UMTC Coursedog Catalog",
                "scraped_at": datetime.datetime.now().isoformat()
            })

        return documents

