# -- Etapa 1: Build
FROM node:22-alpine AS builder

WORKDIR /app

# Copiar manifiestos usando la ruta relativa al contexto raíz (.)
COPY package.json pnpm-lock.yaml ./

# Habilitar pnpm e instalar dependencias
# RUN corepack enable && pnpm install --frozen-lockfile
# RUN corepack enable && pnpm config set allow-builds true && pnpm install --frozen-lockfile
RUN corepack enable && pnpm install --frozen-lockfile --dangerously-allow-all-builds

# Copiar el resto del código del frontend
COPY . .

# Copiar .env para Vite (production override)
COPY .env.production.local .env.production.local

RUN pnpm run build

# -- Etapa 2: Servir con nginx
FROM nginx:alpine

# Copiar build al document root
COPY --from=builder /app/dist /usr/share/nginx/html

# Copiar configuración de nginx para SPA
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
