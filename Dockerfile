# T1 Annotation Service
# 构建：docker build -t t1-annotation:latest .
# 运行：docker run -d -p 8001:8001 --env-file .env --name t1-annotation t1-annotation:latest
#   （.env 参照 .env.example 填好 LLM_BASE_URL 等内网vLLM连接信息）

FROM hlyn3voy1ie4dwn74t.xuanyuan.run/python:3.12-slim

WORKDIR /app

# 系统依赖：几乎不需要额外的系统包，openai/fastapi都是纯Python依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# 非root用户运行
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

EXPOSE 8001

# 健康检查，命中 /health 即可
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# 生产环境不用 --reload，worker数量按实际负载调整
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]
