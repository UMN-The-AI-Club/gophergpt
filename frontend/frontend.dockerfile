# Build stage
FROM node:20-alpine AS builder

WORKDIR /usr/src/app

# The browser will call /api instead of talking directly
# to localhost:8000.
ARG REACT_APP_API_BASE=/api
ENV REACT_APP_API_BASE=${REACT_APP_API_BASE}

COPY package*.json ./

RUN npm ci

COPY . .

RUN npm run build


# Runtime stage
FROM node:20-alpine

WORKDIR /usr/src/app

RUN npm install -g serve

COPY --from=builder /usr/src/app/build ./build

EXPOSE 3000

CMD ["serve", "-s", "build", "-l", "3000"]