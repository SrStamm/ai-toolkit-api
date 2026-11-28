FROM node:22-alpine AS base

RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app

# Install dependencies
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY --from=rag-contracts . /packages/rag-contracts
RUN pnpm install --frozen-lockfile
RUN pnpm --filter @ai-toolkit/rag-contracts build

# Copy source
COPY src ./src
COPY tsconfig.json ./

# Production stage
FROM node:22-alpine AS production

RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY --from=rag-contracts . /packages/rag-contracts
RUN pnpm install --frozen-lockfile
RUN pnpm --filter @ai-toolkit/rag-contracts build

COPY --from=base /app/src ./src
COPY tsconfig.json ./

EXPOSE 3000

CMD ["pnpm", "start"]
