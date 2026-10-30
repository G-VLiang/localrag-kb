"""文档索引：把 Document 内容切片、向量化、写入 doc_chunks。"""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import DocChunk, DocNode, Document, KnowledgeBase
from app.rag.chunker import split_text
from app.rag.embedding import get_embedding_provider
from app.rag.extractor import extract_text


def index_document(db: Session, document: Document) -> int:
    """重建某文档的所有 chunk。返回 chunk 数量。"""
    node = db.get(DocNode, document.node_id)
    if not node:
        return 0

    # 先清空旧 chunk
    db.execute(delete(DocChunk).where(DocChunk.document_id == document.id))

    text = extract_text(document.content, document.content_format)
    if not text:
        db.commit()
        return 0

    chunks_text = split_text(text)
    if not chunks_text:
        db.commit()
        return 0

    provider = get_embedding_provider()
    embeddings = provider.embed(chunks_text)

    for seq, (chunk_text, emb) in enumerate(zip(chunks_text, embeddings)):
        db.add(
            DocChunk(
                document_id=document.id,
                knowledge_base_id=node.knowledge_base_id,
                seq=seq,
                content=chunk_text,
                embedding=emb,
            )
        )
    db.commit()
    return len(chunks_text)


def index_knowledge_base(db: Session, kb_id: str) -> int:
    """重建整个知识库的索引。返回总 chunk 数。"""
    docs = (
        db.query(Document)
        .join(DocNode, DocNode.id == Document.node_id)
        .filter(DocNode.knowledge_base_id == kb_id)
        .all()
    )
    total = 0
    for doc in docs:
        total += index_document(db, doc)
    return total
