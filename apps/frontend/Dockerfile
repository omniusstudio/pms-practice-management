# Production Dockerfile for Frontend
FROM node:24-alpine AS builder

# Build arguments
ARG VERSION=unknown
ARG GIT_SHA=unknown

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies (including dev dependencies for build)
RUN npm ci

# Copy source code
COPY . .

# Create public directory and version file with build information
RUN mkdir -p public && echo "{\"version\":\"${VERSION}\",\"gitSha\":\"${GIT_SHA}\",\"buildTime\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" > public/version.json

# Build the application
RUN npm run build

# Production stage with Nginx
FROM nginx:alpine AS production

# Install curl for health checks
RUN apk add --no-cache curl

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Remove default nginx configuration to avoid conflicts
RUN rm -f /etc/nginx/conf.d/default.conf

# Copy built application from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy version file to dist
COPY --from=builder /app/public/version.json /usr/share/nginx/html/version.json

# Create health check endpoint
RUN echo '{"status":"healthy","service":"pms-frontend"}' > /usr/share/nginx/html/health.json

# Set environment variables
ENV VERSION=${VERSION} \
    GIT_SHA=${GIT_SHA}

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:3000/health.json || exit 1

# Expose port
EXPOSE 3000

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]
