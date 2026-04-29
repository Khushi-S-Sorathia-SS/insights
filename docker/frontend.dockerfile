# Frontend Dockerfile
FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --prefer-offline --no-audit

# Copy application code
COPY . .

# Build the app
RUN npm run build

# Expose port
EXPOSE 3000

# Run the application
CMD ["npm", "start"]
