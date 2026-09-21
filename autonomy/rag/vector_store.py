import os
import psycopg2
from psycopg2.extras import execute_values
from pgvector.psycopg2 import register_vector


def _get_conn():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        user=os.getenv("POSTGRES_USER", "gophergpt"),
        password=os.getenv("POSTGRES_PASSWORD", "gophergpt"),
        dbname=os.getenv("POSTGRES_DB", "gophergpt")
    )


def init_db() -> None:
    """
    Creates the pgvector extension and embeddings table if they don't exist.
    Called once on app startup before serving requests.
    """
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            register_vector(conn)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    id          TEXT PRIMARY KEY,
                    text        TEXT,
                    source_url  TEXT,
                    source_name TEXT,
                    scraped_at  TEXT,
                    chunk_index INTEGER,
                    embedding   vector(1536)
                )
            """)
        conn.commit()


def upsert_chunks(chunks: list[dict], embeddings: list[list[float]]) -> None:
    """
    Inserts or updates a batch of document chunks and their embeddings.

    Args:
        chunks: list of dicts, each with keys text, source_url, source_name, scraped_at, chunk_index
        embeddings: list of float vectors, one per chunk, in the same order as chunks
    """
    rows = [
        (
            f"{chunk['source_url']}::{chunk['chunk_index']}",
            chunk["text"],
            chunk["source_url"],
            chunk["source_name"],
            chunk["scraped_at"],
            chunk["chunk_index"],
            embedding
        )
        for chunk, embedding in zip(chunks, embeddings)
    ]
    with _get_conn() as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            execute_values(cur, """
                INSERT INTO embeddings (id, text, source_url, source_name, scraped_at, chunk_index, embedding)
                VALUES %s
                ON CONFLICT (id) DO UPDATE SET
                    text = EXCLUDED.text,
                    embedding = EXCLUDED.embedding,
                    scraped_at = EXCLUDED.scraped_at
            """, rows)
        conn.commit()


def query_collection(query_embedding: list[float], top_k: int = 5, where: dict | None = None) -> list[dict]:
    """
    Finds the top_k most similar chunks to a given query embedding.

    Args:
        query_embedding: embedded vector of the user's question
        top_k: number of chunks to return, defaults to 5
        where: optional metadata filter e.g. {"source_url": "catalog:CSCI1133"}, pass None for semantic search

    Returns:
        list of dicts each with keys: text, source_url, source_name, distance (lower = more similar)
    """
    with _get_conn() as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            if where and "source_url" in where:
                cur.execute("""
                    SELECT text, source_url, source_name,
                           embedding <=> %s::vector AS distance
                    FROM embeddings
                    WHERE source_url = %s
                    ORDER BY distance
                    LIMIT %s
                """, (query_embedding, where["source_url"], top_k))
            else:
                cur.execute("""
                    SELECT text, source_url, source_name,
                           embedding <=> %s::vector AS distance
                    FROM embeddings
                    ORDER BY distance
                    LIMIT %s
                """, (query_embedding, top_k))
            rows = cur.fetchall()

    return [
        {
            "text": row[0],
            "source_url": row[1],
            "source_name": row[2],
            "distance": round(row[3], 4)
        }
        for row in rows
    ]
