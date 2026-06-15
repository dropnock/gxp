FROM node:22-alpine AS builder
WORKDIR /app

RUN corepack enable

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml turbo.json ./
COPY packages/ts-shared/package.json packages/ts-shared/
COPY apps/runtime/package.json apps/runtime/
RUN pnpm install --frozen-lockfile

COPY packages/ts-shared/ packages/ts-shared/
COPY apps/runtime/ apps/runtime/

ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN pnpm --filter @gxp/runtime build

FROM nginx:1.27-alpine
COPY --from=builder /app/apps/runtime/dist /usr/share/nginx/html
COPY apps/runtime/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
