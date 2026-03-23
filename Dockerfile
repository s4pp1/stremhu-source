# ---- Node.js Build Stage ----
FROM node:22-bookworm-slim AS node-build

WORKDIR /app
ARG APP_VERSION=0.0.0

# Build Server
COPY server ./server
WORKDIR /app/server
RUN node -e "const fs=require('fs');const p=JSON.parse(fs.readFileSync('package.json'));p.version='${APP_VERSION}';fs.writeFileSync('package.json', JSON.stringify(p,null,2));"

RUN npm ci
RUN npm run build
RUN npm prune --omit=dev

# Build Client
WORKDIR /app/client
COPY client ./
RUN npm ci
RUN npm run build

# ---- Python Build Stage ----
FROM python:3.12-slim-bookworm AS python-build

WORKDIR /app/relay

COPY relay/requirements.txt ./

RUN python -m venv /opt/venv && \
  /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# ---- Runtime Stage ----
FROM node:22-bookworm-slim AS runtime

COPY --from=python:3.12-slim-bookworm /usr/local /usr/local

RUN apt-get update && apt-get install -y --no-install-recommends \
  ca-certificates \
  libstdc++6 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=python-build /opt/venv /opt/venv
COPY --from=node-build /app/server/package.json ./server/
COPY --from=node-build /app/server/node_modules ./server/node_modules
COPY --from=node-build /app/server/dist ./server/dist
COPY --from=node-build /app/client/dist ./client/dist
COPY relay /app/relay

# Environment setup
ENV NODE_ENV=production
ENV PYTHONPATH=/app/relay/src
ENV PATH="/opt/venv/bin:/usr/local/bin:${PATH}"
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV SSL_CERT_DIR=/etc/ssl/certs

WORKDIR /app/server

EXPOSE 3000/tcp
EXPOSE 3443/tcp
EXPOSE 6881/tcp 6881/udp

CMD ["node", "dist/main.js"]
