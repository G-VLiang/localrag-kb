"""文档索引：按标题分块 → 切片 → 向量化 → 写入 doc_chunks（含标题路径）。"""

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models import DocChunk, DocNode, Document
from app.rag.chunker import split_text
from app.rag.embedding import get_embedding_provider
from app.rag.extractor import extract_blocks


def index_document(db: Session, document: Document) -> int:
    """重建某文档的所有 chunk。返回 chunk 数量。"""
    node = db.get(DocNode, document.node_id)
    if not node:
        return 0

    # 先清空旧 chunk
    db.execute(delete(DocChunk).where(DocChunk.document_id == document.id))

    blocks = extract_blocks(document.content, document.content_format)
    # meta: (content, heading_path, embed_text)
    meta = []
    for b in blocks:
        path = b.get("path") or ""
        for piece in split_text(b["text"]):
            # 标题路径拼入 embedding 文本，提升按标题语义的召回
            embed_text = f"{path}\n{piece}" if path else piece
            meta.append((piece, path, embed_text))

    if not meta:
        db.commit()
        return 0

    provider = get_embedding_provider()
    embeddings = provider.embed([m[2] for m in meta])

    for seq, ((content, heading, _), emb) in enumerate(zip(meta, embeddings)):
        db.add(
            DocChunk(
                document_id=document.id,
                knowledge_base_id=node.knowledge_base_id,
                seq=seq,
                content=content,
                heading=heading or None,
                embedding=emb,
            )
        )
    db.commit()
    return len(meta)


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
