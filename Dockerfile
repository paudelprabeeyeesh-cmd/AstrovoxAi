# syntax=docker/dockerfile:1

########################
# Stage 1: builder
########################
FROM golang:1.23-alpine AS builder

ARG TARGETOS=linux
ARG TARGETARCH=amd64

RUN apk add --no-cache ca-certificates git

WORKDIR /src

# Cache dependencies first.
COPY go.mod ./
RUN go mod download || true

COPY . .

# Trimpath + stripped for smaller and reproducible binaries.
RUN CGO_ENABLED=0 GOOS=${TARGETOS} GOARCH=${TARGETARCH} \
    go build -trimpath -ldflags="-s -w -X main.version=1.0.0" \
    -o /out/astrovox ./cmd/astrovox

########################
# Stage 2: runtime
########################
FROM gcr.io/distroless/static-debian12:nonroot AS runtime

LABEL org.opencontainers.image.title="astrovox" \
      org.opencontainers.image.description="Astrovox AI inference engine" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.vendor="Astrovox" \
      org.opencontainers.image.licenses="Apache-2.0"

COPY --from=builder /out/astrovox /usr/local/bin/astrovox

# Non-root by default (distroless nonroot user).
USER nonroot:nonroot

EXPOSE 8080
EXPOSE 9090

ENTRYPOINT ["/usr/local/bin/astrovox"]
CMD ["serve", "--port", "8080"]
