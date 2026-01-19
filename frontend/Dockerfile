FROM node:20 AS builder

WORKDIR /app
COPY . .

# Set build-time variables (use default values)
ARG NEXT_PUBLIC_API_BASE_URL=/api/v1
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL

# Install dependencies using official registry
RUN npm install
RUN npm run build

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/node_modules ./node_modules


# Note: API Base URL is set via Nginx
# Start command
CMD ["npm", "start"]