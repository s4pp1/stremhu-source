# ---- Base (Ubuntu + Node.js + Python) ----
FROM ubuntu:24.04 AS base

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates python3 python3-pip python3-venv python-is-python3 \
    && update-ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ---- Build ----
FROM base AS build

ARG APP_VERSION=0.0.0

# Server build
WORKDIR /app/server
COPY server ./

RUN node -e "const fs=require('fs');const p=JSON.parse(fs.readFileSync('package.json'));p.version='${APP_VERSION}';fs.writeFileSync('package.json', JSON.stringify(p,null,2));"

RUN npm ci
RUN npm run build
RUN npm prune --omit=dev

# Client build
WORKDIR /app/client
COPY client ./
RUN npm ci
RUN npm run build

# libtorrent engine dependenciák
WORKDIR /app/libtorrent-engine
COPY libtorrent-engine/requirements.txt ./requirements.txt
COPY libtorrent-engine/logging.prod.ini ./logging.prod.ini
COPY libtorrent-engine/src ./src


RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# ---- Runtime ----
FROM base AS runtime

# Venv átmásolása
COPY --from=build /opt/venv /opt/venv

WORKDIR /app

# Server kód átmásolása a build-ből
COPY --from=build /app/server/package.json ./server/
COPY --from=build /app/server/node_modules ./server/node_modules
COPY --from=build /app/server/dist ./server/dist

# Client átmásolása a build-ből
COPY --from=build /app/client/dist ./client/dist

# libtorrent engine kód és dependencia
COPY --from=build /app/libtorrent-engine /app/libtorrent-engine

WORKDIR /app/server

ENV NODE_ENV=production
ENV PYTHONPATH=/app/libtorrent-engine/src
ENV PATH="/opt/venv/bin:${PATH}"
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV SSL_CERT_DIR=/etc/ssl/certs

EXPOSE 3000/tcp
EXPOSE 3443/tcp
EXPOSE 6881/tcp 6881/udp

CMD ["node", "dist/main.js"]
