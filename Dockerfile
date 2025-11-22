# ---- Build ----
FROM node:22.21.1-slim AS build

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

# ---- Runtime ----
FROM node:22.21.1-slim AS runtime
WORKDIR /app

# Server kód átmásolása a build-ből
COPY --from=build /app/server/package.json ./server/
COPY --from=build /app/server/node_modules ./server/node_modules
COPY --from=build /app/server/dist ./server/dist

# Client átmásolása a build-ből
COPY --from=build /app/client/dist ./client/dist

WORKDIR /app/server

ENV NODE_ENV=production

EXPOSE 3000/tcp
EXPOSE 3443/tcp
EXPOSE 6881/tcp

CMD ["node", "dist/main.js"]
