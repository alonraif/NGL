# Build stage
FROM node:18-alpine as build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

RUN apk add --no-cache inotify-tools openssl

RUN mkdir -p /etc/nginx/runtime /var/www/certbot/.well-known/acme-challenge
RUN mkdir -p /etc/nginx/ssl \
 && openssl req -x509 -nodes -newkey rsa:2048 \
    -out /etc/nginx/ssl/default.crt \
    -keyout /etc/nginx/ssl/default.key \
    -subj "/CN=localhost" \
    -days 3650 >/dev/null 2>&1

COPY --from=build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80 443

ENTRYPOINT ["/entrypoint.sh"]
