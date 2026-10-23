FROM node:22-bookworm-slim AS build
WORKDIR /code
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm install -g pnpm@11.25.0
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
ARG BACKEND_URL=http://backend:8000
ENV BACKEND_URL=$BACKEND_URL
RUN pnpm build

FROM node:22-bookworm-slim
WORKDIR /code
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000
COPY --from=build --chown=node:node /code/.next/standalone ./
COPY --from=build --chown=node:node /code/.next/static ./.next/static
COPY --from=build --chown=node:node /code/public ./public
USER node
EXPOSE 3000
CMD ["node", "server.js"]
