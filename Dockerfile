FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Tokyo

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

# PostgreSQL(Alembic)は廃止し、運用データはGoogle Firestore(スキーマレス)に
# 移行したため、起動時のマイグレーション実行は不要になった。
# ${PORT}はCloud Runが自動的に注入する環境変数（未設定時は8080を使う）。
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
