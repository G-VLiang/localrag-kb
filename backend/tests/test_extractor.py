"""标题路径提取单测。"""

from app.rag.extractor import extract_blocks


def test_markdown_heading_paths():
    md = "# 安装指南\n\n第一步安装。\n\n## 依赖\n\n需要 Python。\n\n# 使用\n\n运行即可。"
    blocks = extract_blocks(md, "markdown")
    paths = [b["path"] for b in blocks]
    assert "安装指南" in paths
    assert "安装指南 > 依赖" in paths
    assert "使用" in paths
    joined = " ".join(b["text"] for b in blocks)
    assert "需要 Python" in joined


def test_html_heading_paths():
    html = "<h1>概述</h1><p>介绍内容。</p><h2>细节</h2><p>细节内容。</p>"
    blocks = extract_blocks(html, "html")
    paths = [b["path"] for b in blocks]
    assert "概述" in paths
    assert "概述 > 细节" in paths
    joined = " ".join(b["text"] for b in blocks)
    assert "细节内容" in joined


def test_plain_has_no_heading():
    assert extract_blocks("纯文本内容", "plain") == [{"path": "", "text": "纯文本内容"}]


def test_empty_content():
    assert extract_blocks("", "html") == []
