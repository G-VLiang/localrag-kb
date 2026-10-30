"""文档内容提取：把 HTML / Markdown / 纯文本统一成纯文本。"""

import re
from html import unescape


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
