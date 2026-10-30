FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    HF_ENDPOINT=https://hf-mirror.com \
    HF_HUB_DISABLE_TELEMETRY=1 \
    HF_HUB_DISABLE_XET=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 可选：安装本地 Embedding 依赖（含 torch，约 2GB，构建较慢）
# 构建时传入 --build-arg INSTALL_RAG_DEPS=1
ARG INSTALL_RAG_DEPS=0
COPY requirements-rag.txt .
RUN if [ "$INSTALL_RAG_DEPS" = "1" ]; then \
      pip install --no-cache-dir -r requirements-rag.txt; \
    fi

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
