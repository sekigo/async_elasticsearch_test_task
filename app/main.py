from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import services
from app.db import engine, get_session, init_db
from app.schemas import DocumentOut, ErrorOut
from app.search import es, init_index


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await init_db()
    await init_index()
    yield
    await es.close()
    await engine.dispose()


app = FastAPI(
    title="Document Search",
    version="1.0.0",
    description="Простой поисковик по текстам документов (PostgreSQL + Elasticsearch).",
    lifespan=lifespan,
)

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@app.get(
    "/documents/search",
    response_model=list[DocumentOut],
    summary="Полнотекстовый поиск документов",
    description=(
        "Ищет по тексту документов в индексе и возвращает первые 20 найденных "
        "документов со всеми полями из БД, упорядоченные по дате создания (новые первыми)."
    ),
    tags=["documents"],
)
async def search_documents(
    session: SessionDep,
    q: Annotated[str, Query(min_length=1, description="Произвольный текстовый запрос")],
) -> list[DocumentOut]:
    docs = await services.search_documents(session, q)
    return [DocumentOut.model_validate(doc) for doc in docs]


@app.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить документ",
    description="Удаляет документ из БД и из поискового индекса по `id`.",
    responses={404: {"model": ErrorOut, "description": "Документ не найден"}},
    tags=["documents"],
)
async def delete_document(
    session: SessionDep,
    document_id: Annotated[int, Path(description="id документа")],
) -> None:
    if not await services.delete_document(session, document_id):
        raise HTTPException(status_code=404, detail="Document not found")
