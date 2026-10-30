"""文档导入解析：PDF / Word / TXT / Markdown → 纯文本或 Markdown。

依赖 markitdown（支持 pdf/docx/pptx 等）与 pypdf 兜底。
优先用 markitdown；未安装时对 PDF 用 pypdf，对 TXT/MD 直接读。
"""

from __future__ import annotations

from io import BytesIO


def parse_bytes(filename: str, data: bytes) -> str:
    """按文件名后缀解析为 Markdown 文本。"""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext in ("md", "markdown", "txt"):
        return data.decode("utf-8", errors="ignore")

    if ext == "pdf":
        return _parse_pdf(data)

    if ext in ("docx", "doc"):
        return _parse_docx(data)

    # 其他格式尝试 markitdown 通用解析
    return _parse_markitdown(filename, data)


def _parse_pdf(data: bytes) -> str:
    # 优先 markitdown
    try:
        return _parse_markitdown("file.pdf", data)
    except Exception:
        pass
    # 兜底 pypdf
    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(data))
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n\n".join(parts)
    except ImportError:
        return "（PDF 解析依赖未安装：请安装 markitdown 或 pypdf）"


def _parse_docx(data: bytes) -> str:
    try:
        return _parse_markitdown("file.docx", data)
    except Exception:
        return "（Word 解析依赖未安装：请安装 markitdown）"


def _parse_markitdown(filename: str, data: bytes) -> str:
    from markitdown import MarkItDown

    md = MarkItDown()
    result = md.convert_stream(BytesIO(data), file_extension=filename.rsplit(".", 1)[-1])
    return result.text_content
