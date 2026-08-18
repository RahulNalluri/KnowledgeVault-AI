FROM node:24.14.0-alpine3.23 AS dependencies

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM dependencies AS development

ENV NODE_ENV=development
COPY --chown=node:node . .
USER node
EXPOSE 3000
CMD ["npm", "run", "dev"]

FROM dependencies AS builder

ARG NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}
COPY . .
RUN npm run build

FROM node:24.14.0-alpine3.23 AS production

ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
ENV PORT=3000
WORKDIR /app
COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static
USER node
EXPOSE 3000
CMD ["node", "server.js"]
