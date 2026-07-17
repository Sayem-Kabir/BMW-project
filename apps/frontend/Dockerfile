FROM node:20-alpine

WORKDIR /app

RUN npm install -g pnpm@9

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# Source is bind-mounted in docker-compose; keep a copy for image-only runs
COPY . .

EXPOSE 3000

# Default for local compose (overridden by docker-compose.yml command)
CMD ["pnpm", "dev", "-H", "0.0.0.0", "-p", "3000"]
