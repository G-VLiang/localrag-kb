# LocalRAG KB — 本地智能 RAG 知识库

语雀式知识沉淀 + RAG 智能检索，本地优先部署，可扩展至团队/企业多用户协作。

## 技术栈

| 层 | 选型 |
|---|---|
| 前端 | React 18 + TypeScript + Vite + Tailwind + Tiptap |
| 后端 | Python 3.11 + FastAPI + SQLAlchemy 2 + Pydantic v2 |
| 数据库 | PostgreSQL 16 + pgvector（关系 + 向量单库） |
| 认证 | JWT（access + refresh） |
| Embedding | bge-m3（本地，可选云 API） |
| LLM | Ollama 本地（qwen2.5），预留 OpenAI 兼容接口 |
| 部署 | Docker Compose |

## 目录结构

```
├── backend/          # FastAPI 后端
│   ├── app/
│   │   ├── main.py   # 应用入口
│   │   ├── config.py # 配置（.env）
│   │   ├── db.py     # 数据库引擎/Session
│   │   ├── models/   # ORM 模型
│   │   ├── schemas/  # Pydantic schema
│   │   ├── api/      # 路由
│   │   └── deps.py   # 依赖注入
│   └── alembic/      # 数据库迁移
├── frontend/         # React 前端
└── docker-compose.yml
```

## 快速开始（Docker 一键部署）

> 适合：企业内网单台服务器全栈部署（生产可用）。
> 前提：已安装 Docker Engine / Docker Desktop。

```bash
# 1. 准备环境变量（至少设置 JWT_SECRET，可用 openssl rand -hex 32 生成）
cp .env.example .env
vim .env                 # 填入 JWT_SECRET 等

# 2. 启动全部服务（nginx 反代 + 前端 + 后端 + 数据库）
docker compose up -d --build

# 3. 访问
#    前端（唯一对外入口）：http://<服务器IP>   （默认 80 端口，可改 WEB_PORT）
#    API 文档（经 nginx 透传）：http://<服务器IP>/docs
```

- 数据库会自动执行 `alembic upgrade head` 建表，pgvector 扩展由镜像内置。
- 后端**不对外暴露端口**，只经 nginx 反代 `/api` 提供服务，攻击面更小。
- 生产环境 `DEBUG=false`，未设置强随机 `JWT_SECRET` 时后端会**启动即拒绝**。
- 可选本地大模型：`docker compose --profile ollama up -d --build`，完全离线推理。

## 本地开发（不用 Docker）

**后端**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # 按需修改 DATABASE_URL 等
alembic upgrade head
uvicorn app.main:app --reload
```

**前端**

```bash
cd frontend
npm install
npm run dev
```

## 启用 RAG 模型（重要）

RAG 检索/问答需要 **Embedding** 和 **LLM** 两个模型能力。系统支持三种组合，在 `backend/.env` 中切换。

### 方案 A：完全本地（推荐，离线隐私最好）

```bash
# 1. 安装 Ollama（https://ollama.com/download/Windows）
# 2. 拉模型
ollama pull bge-m3        # Embedding（约 1.2GB）
ollama pull qwen2.5:7b    # LLM（约 4.7GB）

# 3. 配置 backend/.env
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=bge-m3
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:7b
# 集成式：启用 --profile ollama 时填容器内地址
OLLAMA_BASE_URL=http://ollama:11434
# 或：Ollama 装在宿主机时填（Docker Desktop 默认可用 host.docker.internal）
# OLLAMA_BASE_URL=http://host.docker.internal:11434
```

> 推荐用集成式 `ollama` 服务：`docker compose --profile ollama up -d`，后端通过 `http://ollama:11434` 访问，完全离线、无需宿主机装 Ollama。

### 方案 B：本地 sentence-transformers（不依赖 Ollama 做 Embedding）

```bash
# 方式 1：装进现有容器（快速，但容器重建后会丢失）
bash scripts/install_rag_deps.sh

# 方式 2：固化进镜像（推荐，一次构建长期可用）
INSTALL_RAG_DEPS=1 docker compose build backend
docker compose up -d backend
```

然后配置 `backend/.env`：
```bash
EMBEDDING_PROVIDER=local
EMBEDDING_LOCAL_PATH=BAAI/bge-m3
```
> 首次调用会自动从 HuggingFace 下载 bge-m3 模型（约 2.3GB）。
> 国内网络已默认配置 `HF_ENDPOINT=https://hf-mirror.com` 镜像加速。

### 方案 C：云端 API（最省事，效果最好）

```bash
EMBEDDING_PROVIDER=openai
EMBEDDING_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_API_KEY=sk-xxx
EMBEDDING_MODEL=text-embedding-v3

LLM_PROVIDER=openai
LLM_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_API_KEY=sk-xxx
LLM_MODEL=qwen-plus
```
任何 OpenAI 兼容接口都行（通义/DeepSeek/OpenAI/智谱…）。

### 验证模型是否就绪

```bash
curl http://localhost:8000/api/v1/health
# 打开前端 → 文档编辑器 → 点「重建索引」，右上角会显示「已索引 N 个片段」
```

模型未就绪时接口返回 **503 + 明确中文提示**（不再是 500 报错）。

## 进度

- [x] P0 脚手架 + Docker 环境
- [x] P1 后端基础：认证与组织 CRUD
- [x] P2 前端基础：导航与富文本编辑器
- [x] P3 RAG 核心：切片/向量化/混合检索
- [x] P4 RAG 交互：对话式问答与引用
- [x] P5 企业权限与分享
- [x] P6 增强功能（导入/导出/版本历史/全文搜索）与部署文档

## API 概览（39 个路由）

| 模块 | 前缀 | 说明 |
|---|---|---|
| 认证 | `/api/v1/auth/*` | 注册/登录/刷新/me |
| 空间 | `/api/v1/spaces/*` | 空间 CRUD + 成员管理 |
| 知识库 | `/api/v1/spaces/{id}/kb/*` | 知识库 CRUD |
| 文档 | `/api/v1/kb/{id}/*` | 文档树/内容/导入导出/版本/全文搜索 |
| RAG | `/api/v1/rag/*` | 索引/混合检索/问答 |
| 分享 | `/api/v1/nodes/{id}/share`, `/api/v1/share/access` | 分享链接（密码/有效期） |

## 数据模型

users · spaces · space_members · knowledge_bases · doc_nodes · documents · document_versions · doc_chunks(向量) · share_links

## RAG 说明

- **Embedding**：默认本地 `sentence-transformers` 加载 `BAAI/bge-m3`（1024 维），也可切 Ollama / OpenAI 兼容云 API（改 `.env` 的 `EMBEDDING_PROVIDER`）
- **LLM**：默认 Ollama `qwen2.5:7b`，可切云 API（`LLM_PROVIDER=openai`）
- **混合检索**：pgvector 向量余弦 + BM25 关键词融合（RRF），`doc_chunks` 用 HNSW 索引加速
- 首次运行会下载 bge-m3 模型（约 2GB），请预留空间
