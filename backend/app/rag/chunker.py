"""文档切片：递归按层级分隔符切分，优先在段落/句/逗号边界断开，带重叠。

策略：
1. 依次用「段落 → 换行 → 句号/问叹号 → 分号 → 逗号」等分隔符把文本拆成片段；
2. 把片段顺序合并成 ≤ chunk_size 的窗口，相邻窗口承接尾部 overlap 个字符（保语义连续）；
3. 仍超长的单块做滑动窗口硬切（同样保留重叠）。
"""

from typing import List

from app.config import settings

_SEPARATORS = ["\n\n", "\n", "。", "！", "？", "!", "?", "；", ";", "，", ",", "、"]


def _hard_split(text: str, size: int, overlap: int) -> List[str]:
    step = max(1, size - overlap)
    return [text[i : i + size] for i in range(0, len(text), step)]


def _split_by_separators(text: str, seps: List[str]) -> List[str]:
    """递归按分隔符拆，并把分隔符带在左片段尾部；无法再分则返回原文。"""
    if not seps:
        return [text]
    sep = seps[0]
    parts = text.split(sep)
    if len(parts) == 1:
        return _split_by_separators(text, seps[1:])
    out: List[str] = []
    for i, p in enumerate(parts):
        piece = (p + sep) if i < len(parts) - 1 else p
        if sep and len(piece) > 1:
            out.extend(_split_by_separators(piece, seps[1:]))
        else:
            out.append(piece)
    return out


def split_text(
    text: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> List[str]:
    size = int(chunk_size or settings.chunk_size)
    overlap = int(chunk_overlap if chunk_overlap is not None else settings.chunk_overlap)
    overlap = max(0, min(overlap, size - 1))

    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]

    pieces = _split_by_separators(text, _SEPARATORS)

    chunks: List[str] = []
    buf = ""
    for p in pieces:
        p = p.strip()
        if not p:
            continue
        if len(buf) + len(p) <= size:
            buf += p
        else:
            if buf:
                chunks.append(buf)
            buf = (buf[-overlap:] + p) if overlap else p
            if len(buf) > size:
                chunks.extend(_hard_split(buf, size, overlap))
                buf = ""
    if buf:
        chunks.append(buf)

    # 兜底：任何仍超长的块再做滑动窗口硬切
    final: List[str] = []
    for c in chunks:
        if len(c) <= size:
            final.append(c)
        else:
            final.extend(_hard_split(c, size, overlap))
    return [c.strip() for c in final if c.strip()]
