# Unprivileged nginx runs as UID 101 and listens on 8080, so no root is needed.
# nginx 1.31.7 / Alpine 3.24.2, scanned before pinning this multi-platform digest.
FROM nginxinc/nginx-unprivileged:alpine@sha256:378d0c32f6562f7fd9629170797f57d2b953aa09be983b3daaf4809bb039ca00
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY public/ /usr/share/nginx/html/
EXPOSE 8080
