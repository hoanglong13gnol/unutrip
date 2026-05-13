# Build from repository root: docker build -f backend/rag/Dockerfile backend/rag
FROM python:3.12-slim-bookworm

WORKDIR /svc

ENV PYTHONPATH=/svc \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
