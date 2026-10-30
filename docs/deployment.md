# 部署指南（企业内网服务器）

> 本项目面向**服务器部署**，不建议在单机笔记本上运行（尤其带本地大模型时）。开发机只用来改代码。

## 1. 运行环境

| 项 | 最低 | 推荐 |
|---|---|---|
| CPU / 内存（仅应用） | 2 核 / 4 GB | 4 核 / 8 GB |
| 额外（本地 Ollama + qwen2.5:7b） | +8 GB 内存 | +16 GB，有 GPU 更佳 |
| 磁盘 | 20 GB | 50 GB+（模型与向量索引占空间） |
| 系统 | Linux（推荐）/ Windows Server + Docker Desktop | Ubuntu 22.04 LTS |
| 软件 | Docker Engine 24+ 与 Docker Compose v2 | 同左 |

> 如果企业内网无法访问外网，请先在有网机器上准备好镜像、模型与前端依赖，再离线导入（见第 6 节）。

## 2. 获取代码与配置

```bash
git clone <your-repo-url> localrag-kb
cd localrag-kb
cp .env.example .env
```

编辑 `.env`，**至少**设置：

```ini
JWT_SECRET=<openssl rand -hex 32 生成>
POSTGRES_PASSWORD=<强密码>
ADMIN_EMAILS=admin@your-company.com
```

模型相关配置见 [模型配置](model-setup.md)。

## 3. 启动

```bash
docker compose up -d --build
```

首次启动会自动执行数据库迁移（`alembic upgrade head`）。

访问：`http://<服务器IP>`（默认 80 端口，可在 `.env` 用 `WEB_PORT` 修改）。

- 前端：`/`
- API 文档：`/docs`

## 4. 反向代理与 HTTPS（生产建议）

前面再加一层 Nginx 做 TLS。应用侧 nginx 已监听 80，宿主机可只暴露反代端口。

```nginx
server {
    listen 443 ssl;
    server_name kb.your-company.com;

    ssl_certificate     /etc/nginx/certs/kb.crt;
    ssl_certificate_key /etc/nginx/certs/kb.key;

    client_max_body_size 50m;   # 文档导入

    location / {
        proxy_pass http://127.0.0.1:8080;   # 对应 .env 的 WEB_PORT
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }
}

server {
    listen 80;
    server_name kb.your-company.com;
    return 301 https://$host$request_uri;
}
```

把 `.env` 的 `WEB_PORT` 设为 `8080`、`PUBLIC_BASE_URL` 设为 `https://kb.your-company.com`（影响分享链接）。

## 5. 数据与升级

- 数据库数据在 Docker 卷 `pgdata`；建议按 [运维文档](../README.md#运维企业内网) 定期 `scripts/backup.sh` 备份。
- 升级：`git pull && docker compose up -d --build`（迁移自动执行）。
- 查看日志：`docker compose logs -f backend`。

## 6. 内网/离线部署要点

在可联网机器上准备：

```bash
# 1) 拉取镜像并导出
docker compose pull
docker save -o images.tar pgvector/pgvector:pg16 nginx:1.27-alpine node:22-alpine python:3.11-slim ollama/ollama:latest
# 2) 模型（若用 Ollama）
docker run --rm -v ollama_models:/root/.ollama ollama/ollama pull bge-m3
docker run --rm -v ollama_models:/root/.ollama ollama/ollama pull qwen2.5:7b
```

内网机器导入：

```bash
docker load -i images.tar
docker compose up -d
```

> 前端构建需要 npm 依赖：镜像内已配置 `registry.npmmirror.com`；纯离线环境请在联网机器 `docker compose build web` 后 `docker save` 该镜像。

## 7. 常见问题

| 现象 | 处理 |
|---|---|
| 问答返回 503「Embedding/LLM 未就绪」 | 未配置模型，见 [模型配置](model-setup.md) |
| 页面能开但接口 401 | 未登录或 token 过期，重新登录 |
| 导入大文件失败 | 反代 `client_max_body_size` 调大；或分批 |
| 后端启动报 JWT_SECRET 未设置 | 生产环境必须显式配置强随机 `JWT_SECRET` |
| 端口被占用 | 改 `.env` 的 `WEB_PORT` |
