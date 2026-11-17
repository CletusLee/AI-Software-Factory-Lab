FROM node:24-trixie-slim AS build
RUN apt-get update && apt-get install -y --no-install-recommends python3 make g++ libsqlite3-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY . .
RUN node .yarn/releases/yarn-4.13.0.cjs install
RUN node .yarn/releases/yarn-4.13.0.cjs workspace app build
RUN node .yarn/releases/yarn-4.13.0.cjs build:backend

FROM node:24-trixie-slim
RUN apt-get update && apt-get install -y --no-install-recommends libsqlite3-0 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app /app
RUN tar xzf packages/backend/dist/bundle.tar.gz
CMD ["node", "packages/backend", "--config", "app-config.yaml", "--config", "app-config.production.yaml"]
