# 模型配置（Embedding + LLM）

RAG 的「检索」依赖 **Embedding 模型**，「问答生成」依赖 **LLM**。二者必须至少配置一种组合，否则相关接口返回 **503**。

支持三种方式，任选其一：

| 方式 | Embedding | LLM | 适用 |
|---|---|---|---|
| A 本地 sentence-transformers | bge-m3（本地） | 需另配 LLM（Ollama/云） | 有 GPU/CPU 尚可，完全离线 |
| B Ollama | bge-m3 | qwen2.5:7b 等 | 内网统一模型服务，推荐 |
| C 云 API（OpenAI 兼容） | 云 embedding | 云 LLM | 省事、效果好，需外网 |

---

## ⚠️ 重要：向量维度必须为 1024

数据库 `doc_chunks.embedding` 列是 `Vector(1024)`（见 `backend/app/models/entities.py`）。**默认 bge-m3 是 1024 维**，可直接用。

若你选用的 Embedding 模型不是 1024 维（如 OpenAI `text-embedding-3-small` 是 1536 维），写入会报维度不匹配。两种解法：

1. **优先选 1024 维模型**（bge-m3、通义 `text-embedding-v3` 可选 1024 维）。
2. 改维度：把 `entities.py` 里 `Vector(1024)` 改成对应维度，并新增一个 Alembic 迁移重建该列与索引（改列维度需 `DROP` 旧列/索引后重建）。改完执行 `alembic upgrade head` 并**重新索引所有文档**。

> 更换 Embedding 模型后，历史向量失效，必须在界面「重建索引」或调用 `/api/v1/rag/index`（scope=knowledge_base）重建。

---

## 方式 A：本地 sentence-transformers（bge-m3）

镜像需带 RAG 依赖（含 torch，约 +2GB，构建较慢）：

```bash
INSTALL_RAG_DEPS=1 docker compose build backend
docker compose up -d backend
```

`.env`：

```ini
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=bge-m3
EMBEDDING_LOCAL_PATH=BAAI/bge-m3
```

首次调用会自动从 HuggingFace 下载 bge-m3（约 2GB）。国内网络已默认：

```ini
HF_ENDPOINT=https://hf-mirror.com
HF_HUB_DISABLE_TELEMETRY=1
HF_HUB_DISABLE_XET=1
```

离线部署可预先下载到宿主目录，再挂载并在 `.env` 用 `EMBEDDING_LOCAL_PATH` 指向本地路径。

> 本方式只解决 Embedding；LLM 仍需选 Ollama 或云 API（见 B/C 的 LLM 部分）。

## 方式 B：Ollama（推荐内网）

```bash
docker compose --profile ollama up -d
docker exec -it localrag-ollama ollama pull bge-m3
docker exec -it localrag-ollama ollama pull qwen2.5:7b
```

`.env`：

```ini
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=bge-m3
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:7b
OLLAMA_BASE_URL=http://ollama:11434
```

若 Ollama 装**宿主机**而非容器：

- Docker Desktop：`OLLAMA_BASE_URL=http://host.docker.internal:11434`
- Linux 宿主机：用宿主内网 IP，或给 backend 加 `extra_hosts: ["host.docker.internal:host-gateway"]`

## 方式 C：云 API（OpenAI 兼容）

`.env` 示例（通义 DashScope）：

```ini
EMBEDDING_PROVIDER=openai
EMBEDDING_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_API_KEY=sk-xxx
EMBEDDING_MODEL=text-embedding-v3      # 选 1024 维

LLM_PROVIDER=openai
LLM_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_API_KEY=sk-xxx
LLM_MODEL=qwen-plus
```

DeepSeek / OpenAI / 智谱等任何 OpenAI 兼容接口同理。

---

## 验证是否配置成功

1. 健康检查：`curl http://<服务器>/api/v1/health`
2. 登录后建文档并「保存」（自动索引），右上角显示「已索引 N 个片段」即 Embedding 通。
3. 「智能问答」提问能返回答案与引用即 LLM 通。

## 常见错误

| 错误 | 原因 | 处理 |
|---|---|---|
| 503 Embedding 未就绪 | 未装 sentence-transformers 或模型没下完 | 改用 ollama/openai，或 `INSTALL_RAG_DEPS=1` 构建 |
| 503 LLM 未连接 | Ollama 没起/模型没拉/地址错 | 检查 `OLLAMA_BASE_URL`、`ollama list` |
| 维度不匹配 | Embedding 非 1024 维 | 见上方「向量维度」 |
| 下载模型超时 | 国外网络 | 用 `HF_ENDPOINT` 镜像或离线挂载 |

## 检索相关可调项（`.env`，默认已较优）

```ini
USE_RERANK=true          # 词法重排
USE_MMR=true             # 多样性重排
MMR_LAMBDA=0.7
PARENT_EXPAND=true       # 父块上下文扩展
PARENT_WINDOW=1
MAX_CONTEXT_CHARS=6000   # 喂给 LLM 的上下文预算
RERANK_PROVIDER=lexical  # 或 cross-encoder（需 sentence-transformers + 模型）
USE_QUERY_REWRITE=false  # LLM 多路查询（增延迟，按需开）
QUERY_REWRITE_COUNT=3
```
