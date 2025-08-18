# 多阶段构建 - 前端构建阶段
FROM node:18-alpine AS builder

WORKDIR /app

# 复制package.json和package-lock.json
COPY package*.json ./

# 安装依赖
RUN npm install

# 复制源代码（.dockerignore会排除node_modules等）
COPY . .

# 构建项目
ENV NODE_ENV=production
RUN npm run build

# Nginx 提供静态文件服务
FROM nginx:alpine

# 复制构建好的文件到nginx默认目录
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制nginx配置文件
COPY nginx.conf /etc/nginx/nginx.conf

# 暴露端口
EXPOSE 80

# 启动nginx
CMD ["nginx", "-g", "daemon off;"]