FROM node:22.20.0-alpine@sha256:dbcedd8aeab47fbc0f4dd4bffa55b7c3c729a707875968d467aaaea42d6225af AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginx:1.30.8-alpine@sha256:8eb04fe3b385090e9aa02961f77398ad09b6bf33ab07f6669a5bb7acce22c0d3
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/site.template
COPY nginx-main.conf /etc/nginx/nginx.conf
COPY --chmod=0555 start-nginx.sh /start-nginx.sh
USER 101:101
EXPOSE 8080
ENTRYPOINT ["/start-nginx.sh"]
