# ==============================================================================
# Multi-Stage Dockerfile for Nginx Reverse Proxy & React Production Gateway
# ==============================================================================

# Stage 1: Build production React/Vite assets
FROM node:22-alpine AS build

WORKDIR /app

# Copy dependency manifests first for layer caching
COPY frontend/package.json frontend/package-lock.json ./

# Clean installation of dependencies using lockfile
RUN npm ci

# Copy frontend source files and configuration
COPY frontend/ ./

# Compile production bundle into /app/dist
RUN npm run build

# Stage 2: Serve via high-performance Nginx gateway
FROM nginx:alpine

# Remove default static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy compiled frontend assets from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy repository Nginx configuration
COPY nginx/default.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
