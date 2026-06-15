FROM node:22-alpine AS builder
WORKDIR /app

RUN corepack enable

# Install dependencies
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml turbo.json ./
COPY packages/ts-shared/package.json packages/ts-shared/
COPY apps/portal/package.json apps/portal/
RUN pnpm install --frozen-lockfile

# Build
COPY packages/ts-shared/ packages/ts-shared/
COPY apps/portal/ apps/portal/

ARG VITE_KEYCLOAK_URL
ARG VITE_API_BASE_URL
ENV VITE_KEYCLOAK_URL=${VITE_KEYCLOAK_URL}
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN pnpm --filter @gxp/portal build

FROM nginx:1.27-alpine
COPY --from=builder /app/apps/portal/dist /usr/share/nginx/html
COPY apps/portal/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
