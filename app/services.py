from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import search
from app.config import settings
from app.models import Document


async def search_documents(session: AsyncSession, query: str) -> list[Document]:
    """Берёт из индекса первые N релевантных документов и сортирует их по дате создания."""
    ids = await search.search_ids(query, settings.search_limit)
    if not ids:
        return []
    stmt = (
        select(Document)
        .where(Document.id.in_(ids))
        .order_by(Document.created_date.desc(), Document.id)
    )
    return list(await session.scalars(stmt))


async def delete_document(session: AsyncSession, doc_id: int) -> bool:
    """Удаляет документ из БД и индекса. Возвращает False, если документа не было в БД."""
    result = await session.execute(delete(Document).where(Document.id == doc_id))
    # Удаляем из индекса до коммита: если эластик недоступен, транзакция откатится.
    await search.delete_from_index(doc_id)
    await session.commit()
    return result.rowcount > 0
