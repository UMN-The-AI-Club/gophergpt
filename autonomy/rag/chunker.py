def chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> list[dict]:
    """
    Splits a long string of text into smaller overlapping passages (chunks).

    Called by the indexer after scraping a UMN page — the raw page text gets
    passed here before being embedded and stored in ChromaDB. Smaller chunks
    produce more precise search results than storing a whole page as one document.

    Each returned dict will have:
        - text:        the passage text
        - chunk_index: position of this chunk in the original document (0, 1, 2...)
    
    Parameters:
        text:       the full raw text to split
        chunk_size: how many words per chunk (default 400)
        overlap:    how many words to repeat between adjacent chunks (default 50)
                    this prevents losing context at chunk boundaries
    """
    words = text.split()
    chunks = []
    for chunk_index, i in enumerate(range(0, len(words), chunk_size - overlap)):
        chunks.append({
            "text": " ".join(words[i : i + chunk_size]),
            "chunk_index": chunk_index
        })
    

    return chunks