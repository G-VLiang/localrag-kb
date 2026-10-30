#!/usr/bin/env bash
# 在运行中的后端容器里安装 RAG 依赖（sentence-transformers + torch）
# 用法： bash scripts/install_rag_deps.sh
set -euo pipefail

CONTAINER="${CONTAINER:-kb-backend}"
PIP_INDEX="${PIP_INDEX:-https://pypi.tuna.tsinghua.edu.cn/simple}"

echo "==> 检查容器 ${CONTAINER} 是否运行"
if ! docker ps --format '{{.Names}}' | grep -qx "${CONTAINER}"; then
  echo "容器 ${CONTAINER} 未运行，请先执行：docker compose up -d db && docker run -d --name ${CONTAINER} ..."
  exit 1
fi

echo "==> 安装 RAG 依赖（torch 约 2GB，请耐心等待）"
docker exec "${CONTAINER}" pip install -i "${PIP_INDEX}" --no-cache-dir sentence-transformers==3.3.1

echo "==> 安装完成，验证导入"
docker exec "${CONTAINER}" python -c "import sentence_transformers; print('sentence-transformers OK', sentence_transformers.__version__)"

cat <<'EOF'

✅ 安装成功

接下来：
1. 在 backend/.env 中设置 EMBEDDING_PROVIDER=local（本地模型）或 ollama
2. 首次调用会自动下载 BAAI/bge-m3 模型（约 2.3GB）到容器内
3. 重启后端容器：docker restart kb-backend
4. 打开前端 → 编辑文档 → 点「重建索引」验证

注意：当前 pip 安装只对运行中的容器有效，容器重建后会丢失。
若要持久化，请把 requirements-rag.txt 的内容合并进 backend/requirements.txt 并重新 build 镜像。
EOF
