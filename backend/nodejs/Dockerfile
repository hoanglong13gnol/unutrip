# UNUtrip — Backend API (Express)
# Build: docker compose build backend
FROM node:20-bookworm-slim

WORKDIR /app

RUN apt-get update \
  && apt-get install -y --no-install-recommends ca-certificates \
  && rm -rf /var/lib/apt/lists/*

COPY package.json package-lock.json ./

RUN npm ci --omit=dev

COPY . .

EXPOSE 3000

# NODE_ENV do docker-compose (hoặc `docker run -e`) đặt; không hardcode production để tránh lỗi JWT khi forgot secret lúc dev

CMD ["node", "src/index.js"]
