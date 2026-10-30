# LocalRAG KB — 企业内网智能知识库（RAG）

语雀式知识沉淀 + RAG 智能问答，面向**团队/企业内网私有化部署**。

团队成员把日常知识与经验沉淀为文档；任何人需要**顶替同事处理问题时**，用智能问答快速检索到答案与出处。

## 特性

- **团队协作**：团队空间、成员邀请（邮箱）、角色（owner/admin/editor/reader）
- **知识沉淀**：知识库 + 文档树（文件夹/重命名/移动/删除）+ Tiptap 富文本编辑；导入 PDF/Word/Markdown/TXT（**自动建索引**）；版本历史；导出；分享链接（密码/有效期）
- **高质量 RAG**：标题感知切片、向量 + 关键词混合检索、RRF 融合、词法重排、MMR 多样性、父块上下文扩展（Small-to-Big）、可选 cross-encoder 精排、可选 LLM 多路查询；答案带引用（文档 › 章节），**点击引用直达原文**
- **审计合规**：写操作自动留痕；普通用户自助查看，管理员（`ADMIN_EMAILS`）查看全局
- **生产级部署**：Nginx 静态托管 + `/api` 反代；backend 仅内网暴露；debug 默认关、生产强制 `JWT_SECRET`、CORS 白名单
- **运维**：`scripts/backup.sh` / `restore.sh`；pytest + GitHub Actions CI
- **多模型接入**：本地 sentence-transformers / Ollama / OpenAI 兼容云 API

## 技术栈

| 层 | 选型 |
|---|---|
| 前端 | React 18 + TypeScript + Vite + Tailwind + Tiptap |
| 后端 | Python 3.11 + FastAPI + SQLAlchemy 2 + Pydantic v2 + Alembic |
| 数据库 | PostgreSQL 16 + pgvector（关系 + 向量单库） |
| 鉴权 | JWT（access + refresh）+ bcrypt |
| 部署 | Docker Compose（db / backend / web(nginx) / ollama 可选） |

## 快速开始（服务器部署）

> 面向服务器。单机笔记本不建议跑本地大模型；开发机只用来改代码。

```bash
git clone <your-repo-url> localrag-kb
cd localrag-kb
cp .env.example .env
# 编辑 .env：JWT_SECRET、POSTGRES_PASSWORD、ADMIN_EMAILS，并配置模型
docker compose up -d --build
```

访问 `http://<服务器IP>`（默认 80，可改 `WEB_PORT`）；API 文档 `/docs`。

- 部署细节：[docs/deployment.md](docs/deployment.md)
- **模型配置（必读）**：[docs/model-setup.md](docs/model-setup.md)
- 团队使用流程：[docs/usage.md](docs/usage.md)
- 架构说明：[docs/architecture.md](docs/architecture.md)

## 配置（`.env` 关键项）

| 变量 | 说明 |
|---|---|
| `JWT_SECRET` | **生产必填**，强随机（`openssl rand -hex 32`） |
| `POSTGRES_PASSWORD` | 数据库密码 |
| `WEB_PORT` | 对外端口，默认 80 |
| `ADMIN_EMAILS` | 全局管理员邮箱，逗号分隔 |
| `EMBEDDING_PROVIDER` | `local` / `ollama` / `openai` |
| `LLM_PROVIDER` | `ollama` / `openai` |
| `OLLAMA_BASE_URL` | 默认 `http://ollama:11434` |
| `EMBEDDING_API_BASE/KEY/MODEL` | 云 embedding（需 1024 维） |
| `LLM_API_BASE/KEY/MODEL` | 云 LLM |
| `USE_RERANK` / `USE_MMR` / `PARENT_EXPAND` | 检索增强开关（默认 true） |
| `RERANK_PROVIDER` | `lexical`（零依赖）/ `cross-encoder` |
| `USE_QUERY_REWRITE` | LLM 多路查询（默认 false，增延迟） |
| `PUBLIC_BASE_URL` | 分享链接使用的站点地址 |

> 完整变量见 [.env.example](.env.example)。

## 项目结构

```
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── api/             # 路由：auth/spaces/knowledge_bases/documents/rag/share/audit
│   │   ├── core/            # 安全、审计中间件、角色
│   │   ├── models/          # ORM
│   │   ├── schemas/         # Pydantic
│   │   ├── rag/             # 切片/提取/embedding/检索/重排/LLM
│   │   └── config.py
│   ├── alembic/             # 迁移（0001~0006）
│   └── tests/               # pytest
├── frontend/                # React 前端（Vite）
├── docs/                    # 部署/模型/使用/架构文档
├── scripts/                 # backup.sh / restore.sh / install_rag_deps.sh
├── docker-compose.yml
└── .github/workflows/ci.yml
```

## API 概览

| 模块 | 前缀 |
|---|---|
| 认证 | `/api/v1/auth/*` |
| 空间与成员 | `/api/v1/spaces/*` |
| 知识库 | `/api/v1/spaces/{id}/kb/*` |
| 文档 | `/api/v1/kb/{id}/*`（树/内容/导入/导出/版本/搜索） |
| RAG | `/api/v1/rag/*`（index/search/ask） |
| 分享 | `/api/v1/nodes/{id}/share`、`/api/v1/share/access` |
| 审计 | `/api/v1/audit`、`/api/v1/audit/all`（管理员） |

## 开发与测试

**后端**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env        # 本地开发需 DEBUG=true 或设置 JWT_SECRET
alembic upgrade head
uvicorn app.main:app --reload
pytest
```

**前端**

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173，/api 代理到 8000
npm run build
```

CI：`.github/workflows/ci.yml` 在 push/PR 时跑后端 pytest 与前端构建。

## 运维

```bash
bash scripts/backup.sh                     # 备份到 ./backups/*.sql.gz
bash scripts/restore.sh ./backups/xxx.sql.gz
```

管理员审计：`.env` 设 `ADMIN_EMAILS=admin@corp.com`，「操作日志」页可切「全部」。
上线检查清单见 [README 运维章节](#运维) 与 [docs/deployment.md](docs/deployment.md)。

## 已知限制 / 路线图

- 空间级权限（暂无文档级细粒度权限）
- 未内置 SSO/LDAP（可基于现有 JWT 扩展）
- 向量维度固定 1024（换非 1024 维 embedding 需改 schema，见模型文档）
- backend 单进程 uvicorn（小团队足够，可换 gunicorn/uvicorn workers 扩展）
- cross-encoder 精排需额外依赖与模型（默认词法重排零依赖）

## 许可证

[MIT](LICENSE)
