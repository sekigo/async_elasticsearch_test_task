"""Загрузка CSV в PostgreSQL и Elasticsearch.

Использование: python -m app.load_data data/posts.csv [--batch-size 1000]

Ожидаемые колонки: text, created_date, rubrics и необязательная id.
Если id нет, документы нумеруются по порядку строк начиная с 1.
Существующие данные в таблице и индексе перезаписываются.
"""

import argparse
import ast
import asyncio
import csv
import sys
from datetime import datetime
from typing import Any

from sqlalchemy import insert, text

from app.config import settings
from app.db import engine, init_db, session_factory
from app.models import Document
from app.search import es, index_documents, init_index

csv.field_size_limit(sys.maxsize)


def parse_rubrics(raw: str) -> list[str]:
    raw = raw.strip()
    if not raw:
        return []
    return [str(rubric) for rubric in ast.literal_eval(raw)]


def parse_row(line_no: int, row: dict[str, str]) -> dict[str, Any]:
    return {
        "id": int(row["id"]) if row.get("id") else line_no,
        "text": row["text"],
        "rubrics": parse_rubrics(row["rubrics"]),
        "created_date": datetime.fromisoformat(row["created_date"]),
    }


async def save_batch(batch: list[dict[str, Any]]) -> None:
    async with session_factory() as session:
        await session.execute(insert(Document), batch)
        await session.commit()
    await index_documents(batch)


async def load(path: str, batch_size: int) -> int:
    await init_db()
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE TABLE {Document.__tablename__}"))
    await init_index(recreate=True)

    total = 0
    batch: list[dict[str, Any]] = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for line_no, row in enumerate(csv.DictReader(f), start=1):
            batch.append(parse_row(line_no, row))
            if len(batch) >= batch_size:
                await save_batch(batch)
                total += len(batch)
                batch = []
                print(f"loaded {total}")
        if batch:
            await save_batch(batch)
            total += len(batch)

    await es.indices.refresh(index=settings.es_index)
    return total


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", help="путь к CSV-файлу")
    parser.add_argument("--batch-size", type=int, default=1000)
    args = parser.parse_args()
    try:
        total = await load(args.path, args.batch_size)
        print(f"done: {total} documents")
    finally:
        await es.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
