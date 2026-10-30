"""文档内容提取：把 HTML / Markdown / 纯文本统一成纯文本。"""

import re
from html import unescape
from typing import Dict, List


def strip_html(html: str) -> str:
    """把 Tiptap 产出的 HTML 转成纯文本（近似）。"""
    # 块级标签转成换行
    text = re.sub(r"<(br|/p|/div|/h[1-6]|/li|/tr)>", "\n", html, flags=re.IGNORECASE)
    # 去掉所有标签
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    # 压缩多余空行
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def markdown_to_text(md: str) -> str:
    """Markdown 粗转文本。"""
    text = re.sub(r"```.*?```", " ", md, flags=re.DOTALL)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)  # 图片
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)  # 链接保留文字
    text = re.sub(r"[#>*\-+]+\s?", " ", text)  # 标记符
    text = re.sub(r"`([^`]*)`", r"\1", text)  # 行内代码
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def extract_text(content: str, content_format: str) -> str:
    if content_format == "markdown":
        return markdown_to_text(content)
    if content_format == "html":
        return strip_html(content)
    # plain / txt 直接返回
    return content


_HEADING_RE = re.compile(r"<h([1-6])[^>]*>(.*?)</h\1>", re.IGNORECASE | re.DOTALL)
_MD_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def _strip_tags(s: str) -> str:
    return unescape(re.sub(r"<[^>]+>", "", s)).strip()


def _html_blocks(html: str) -> List[Dict[str, str]]:
    blocks: List[Dict[str, str]] = []
    stack: List[tuple] = []  # (level, text)
    pos = 0

    def cur_path() -> str:
        return " > ".join(t for _, t in stack)

    def flush(segment: str) -> None:
        txt = strip_html(segment)
        if txt:
            blocks.append({"path": cur_path(), "text": txt})

    for m in _HEADING_RE.finditer(html):
        flush(html[pos : m.start()])
        level = int(m.group(1))
        text = _strip_tags(m.group(2))
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, text))
        pos = m.end()
    flush(html[pos:])
    return blocks


def _markdown_blocks(md: str) -> List[Dict[str, str]]:
    blocks: List[Dict[str, str]] = []
    stack: List[tuple] = []
    buf: List[str] = []

    def cur_path() -> str:
        return " > ".join(t for _, t in stack)

    def flush() -> None:
        if buf:
            txt = markdown_to_text("\n".join(buf)).strip()
            if txt:
                blocks.append({"path": cur_path(), "text": txt})
            buf.clear()

    for line in md.splitlines():
        m = _MD_HEADING_RE.match(line.strip())
        if m:
            flush()
            level = len(m.group(1))
            text = m.group(2).strip()
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, text))
        else:
            buf.append(line)
    flush()
    return blocks


def extract_blocks(content: str, content_format: str) -> List[Dict[str, str]]:
    """把文档解析为带标题路径的文本块：[{"path": "一级 > 二级", "text": "..."}]。"""
    if not content or not content.strip():
        return []
    if content_format == "markdown":
        return _markdown_blocks(content)
    if content_format == "html":
        return _html_blocks(content)
    return [{"path": "", "text": content.strip()}]
