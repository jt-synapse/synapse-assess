FROM node:24.22.1-bookworm-slim
WORKDIR /platform
RUN npm install --global pnpm@10.32.1
ENV NEXT_TELEMETRY_DISABLED=1
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY packages/contracts/package.json packages/contracts/package.json
COPY apps/web/package.json apps/web/package.json
RUN pnpm install --frozen-lockfile
COPY packages/contracts/generated packages/contracts/generated
COPY apps/web apps/web
RUN pnpm --filter @synapse/web build && chown -R node:node /platform/apps/web/.next
USER node
CMD ["pnpm", "--filter", "@synapse/web", "start"]
