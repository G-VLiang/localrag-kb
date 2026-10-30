# 架构说明

## 组成

```
┌─────────────┐     /api 反向代理      ┌──────────────┐
│  Nginx(web) │ ───────────────────▶ │  FastAPI     │
│  静态前端    │                       │  backend     │
└─────────────┘                       └──────┬───────┘
                                             │ SQLAlchemy
                                      ┌──────▼────────┐
                                      │ PostgreSQL 16 │
                                      │ + pgvector    │
                                      └───────────────┘
                                             ▲
                          Embedding / LLM 调用 │
                              ┌──────────────┴──────────────┐
                              │ 本地 ST / Ollama / 云 API    │
                              └─────────────────────────────┘
```

- **前端**：React + Vite + TypeScript + Tailwind + Tiptap（富文本）。
- **后端**：FastAPI + SQLAlchemy 2 + Pydantic v2 + Alembic。
- **数据库**：PostgreSQL 16 + pgvector（关系与向量单库）。
- **web 容器**：构建前端静态资源，nginx 托管并反代 `/api` 到 backend。

## 数据模型

`users` · `spaces` · `space_members` · `knowledge_bases` · `doc_nodes`（文档树）· `documents` · `document_versions` · `doc_chunks`（切片+向量）· `share_links` · `audit_logs`

## RAG 流水线

**索引（写入）**
1. 解析内容（HTML/Markdown/纯文本），按标题层级切块（`extractor.extract_blocks`）。
2. 递归分层分隔符切片 + 重叠（`chunker.split_text`）。
3. 标题路径拼入待嵌入文本，调用 Embedding（`indexer.index_document`）。
4. 写入 `doc_chunks`（content / heading / embedding），HNSW 索引加速。

**检索（问答）**
1. （可选）LLM 改写为多路查询（`query.rewrite_queries`）。
2. 每路：向量余弦召回 + BM25/ILIKE 关键词召回 → RRF 融合累加。
3. 相关性打分：cross-encoder（可选）或词法重排（`tokenizer.lexical_score`）。
4. MMR 多样性选择。
5. 父块上下文扩展（邻块补全 + 去重 + 字符预算）。
6. 组装带 `[i]` 引用的提示，调用 LLM 生成答案（`llm.generate_answer`）。

## 鉴权与权限

- JWT（access + refresh）；`get_current_user` 解析令牌。
- 空间级角色校验：读需成员；写需 owner/admin/editor；删库需 owner/admin；删空间需 owner。
- 全局管理员：`ADMIN_EMAILS` 配置判定，可查看全局审计。

## 审计

`AuditMiddleware` 拦截所有写请求（POST/PUT/PATCH/DELETE），解析 token 得 user_id，按路径映射语义动作，落库 `audit_logs`；登录/注册在接口内显式记录成败。审计失败不影响业务。

## 部署形态

`docker-compose.yml` 四服务：`db` / `backend`（内部 8000，不对外）/ `web`（nginx:80）/ `ollama`（可选 profile）。
