# MinIO server built from source.
# Upstream stopped publishing container images and archived the repository,
# so we build the last release tag ourselves and publish it to GHCR.
#
#   docker build -t ghcr.io/winty5959/album-minio:RELEASE.2025-10-15T17-29-55Z infra/minio
ARG MINIO_TAG=RELEASE.2025-10-15T17-29-55Z

FROM golang:1.27.2-alpine3.24 AS build
ARG MINIO_TAG
# Keep a patched local toolchain instead of downloading the archived go.mod toolchain.
ENV CGO_ENABLED=0 GOTOOLCHAIN=local
RUN apk add --no-cache git
WORKDIR /src
RUN git clone --depth 1 --branch "${MINIO_TAG}" https://github.com/minio/minio.git .
# Freeze the patched module graph and checksums, including build-tool dependencies.
COPY go.mod go.sum ./
RUN LDFLAGS="$(MINIO_RELEASE=RELEASE go run -mod=readonly buildscripts/gen-ldflags.go)" \
 && go build -mod=readonly -tags kqueue -trimpath -ldflags "${LDFLAGS}" -o /out/minio .

FROM alpine:3.24
ARG MINIO_TAG
LABEL org.opencontainers.image.source="https://github.com/winty5959/kube-study" \
      org.opencontainers.image.description="MinIO ${MINIO_TAG} built from archived upstream source (AGPL-3.0)" \
      org.opencontainers.image.licenses="AGPL-3.0-only"
RUN apk add --no-cache ca-certificates curl \
 && adduser -D -u 10001 minio \
 && mkdir -p /data && chown minio /data
COPY --from=build /out/minio /usr/bin/minio
USER 10001
VOLUME ["/data"]
EXPOSE 9000 9001
ENTRYPOINT ["/usr/bin/minio"]
CMD ["server", "/data", "--console-address", ":9001"]
