import csv
import datetime
import logging

logger = logging.getLogger(__name__)

# stamped onto every chunk the catalog loaders produce, and the marker the startup
# hook looks for to decide whether the catalog has actually been indexed yet
CATALOG_SOURCE_NAME = "UMTC Coursedog Catalog"

# the exact Coursedog column headers this parser reads — validated up front so a
# wrong or partial export fails naming the missing columns, instead of raising a
# bare KeyError partway through the file
REQUIRED_COLUMNS = (
    "Course subject code",
    "Course number",
    "Course name",
    "Course description",
    "Minimum credits",
    "Maximum credits",
    "Requirements",
    "Typically offered term(s)",
)


def build_course_document(
    code: str,
    name: str,
    description: str,
    min_credits,
    max_credits,
    typically_offered: str,
) -> dict:
    """
    Builds one indexable document from a course, whatever source it came from.

    Shared by the CSV loader and the Coursedog API loader so the two cannot drift
    into producing differently-shaped chunks for the same course.

    `code` must already be normalised the way course_search's exact-match filter
    expects — subject and number joined with no space, keeping any W/H suffix
    (e.g. "CSCI3081W"), because it becomes the source_url.

    Returns:
        a dict with keys text, source_url, source_name, scraped_at.
    """
    text = (
        f"{code} - {name}\n"
        f"Description: {description}\n"
        f"Minimum Credits: {min_credits}\n"
        f"Maximum Credits: {max_credits}\n"
        f"Typically Offered: {typically_offered}"
    )

    return {
        "text": text,
        "source_url": f"catalog:{code}",
        "source_name": CATALOG_SOURCE_NAME,
        "scraped_at": datetime.datetime.now().isoformat(),
    }


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

        missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(
                f"{path} is missing required column(s): {', '.join(missing)}. "
                f"Found: {', '.join(reader.fieldnames or ['<empty file>'])}"
            )

        documents = []
        skipped = 0
        for row in reader:
            if not (row["Course description"] or "").strip():
                skipped += 1
                continue

            # 'Requirements' is deliberately not indexed: in the real export it
            # holds department codes ("013040", "-"), not prerequisites. Actual
            # prerequisites appear inline in the description ("prereq: ...").
            documents.append(build_course_document(
                code=f"{row['Course subject code']}{row['Course number']}",
                name=row["Course name"],
                description=row["Course description"],
                min_credits=row["Minimum credits"],
                max_credits=row["Maximum credits"],
                typically_offered=row["Typically offered term(s)"],
            ))

        logger.info(
            "Parsed %d courses from %s (%d row(s) skipped for empty descriptions).",
            len(documents), path, skipped,
        )

        return documents

