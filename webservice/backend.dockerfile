FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /usr/src/app

RUN pip install --upgrade pip

COPY pyproject.toml README.md ./

RUN pip install --no-build-isolation --no-deps . || pip install \
    "langchain>=0.3.25,<0.4.0" \
    "langgraph>=0.4.8,<0.5.0" \
    "langchain-openai>=0.3.22,<0.4.0" \
    "langchain-tavily>=0.2.3,<0.3.0" \
    "python-dotenv>=1.1.0,<2.0.0" \
    "streamlit>=1.49.1,<2.0.0" \
    "fastapi>=0.118.2,<0.119.0" \
    "uvicorn>=0.37.0,<0.38.0" \
    "pgvector>=0.3.0" \
    "psycopg2-binary>=2.9.0" \
    "httpx>=0.27.0" \
    "beautifulsoup4>=4.12.0" \
    "sqlalchemy>=2.0.51,<3.0.0" \
    "alembic>=1.16.5,<2.0.0" \
    "redis>=5.0.0"

COPY . .

EXPOSE 8000

CMD ["uvicorn", "webservice.app:app", "--host", "0.0.0.0", "--port", "8000"]