"""文档切片：按字符窗口 + 重叠切分，优先在段落/句边界断开。"""

import re
from typing import List

from app.config import settings


def split_text(text: str, chunk_size: int | None = None, chunk_overlap: int | None = None) -> List[str]:
    size = chunk_size or settings.chunk_size
    overlap = chunk_overlap or settings.chunk_overlap

    text = text.strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]

    # 按段落/句边界预切，避免从词语中间切断
    segments = re.split(r"(?<=[。！？!?\n])", text)
    chunks: List[str] = []
    buf = ""
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        # 单个片段超长则硬切
        if len(seg) > size:
            if buf:
                chunks.append(buf)
                buf = ""
            for i in range(0, len(seg), size - overlap):
                chunks.append(seg[i : i + size])
            continue
        if len(buf) + len(seg) <= size:
            buf += seg
        else:
            if buf:
                chunks.append(buf)
            # 重叠：带上上一段结尾
            buf = buf[-overlap:] + seg if overlap > 0 and buf else seg
    if buf:
        chunks.append(buf)

    # 去空白片段
    return [c.strip() for c in chunks if c.strip()]
