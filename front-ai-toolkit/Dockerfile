# -- Etapa 1: Build
FROM node:20-alpine AS builder

WORKDIR /app

# Copiar todo lo necesario para build
COPY front-ai-toolkit/package*.json ./
RUN npm install

# Instalar types faltantes
RUN npm install --save-dev @types/react-syntax-highlighter

COPY front-ai-toolkit/ ./

# Copiar .env para Vite (VITE_* variables se injectan en build time)
COPY front-ai-toolkit/.env .env.production.local

RUN npm run build

# -- Etapa 2: Servir con nginx
FROM nginx:alpine

# Copiar build al document root
COPY --from=builder /app/dist /usr/share/nginx/html

# Copiar configuración de nginx para SPA
COPY front-ai-toolkit/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]