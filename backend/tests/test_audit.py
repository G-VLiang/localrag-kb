"""审计动作映射单测。"""

from app.core.audit import _action_name


def test_action_name_mapping():
    assert _action_name("POST", "/api/v1/auth/login") == "登录"
    assert _action_name("POST", "/api/v1/auth/register") == "注册"
    assert _action_name("PUT", "/api/v1/kb/abc/nodes/xyz/content") == "保存文档"
    assert _action_name("POST", "/api/v1/kb/abc/nodes") == "新建节点"
    assert _action_name("PATCH", "/api/v1/kb/abc/nodes/xyz") == "修改节点"
    assert _action_name("DELETE", "/api/v1/kb/abc/nodes/xyz") == "删除节点"
    assert _action_name("POST", "/api/v1/rag/index") == "重建索引"
    assert _action_name("GET", "/api/v1/unknown") == "GET /api/v1/unknown"
