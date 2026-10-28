FROM node:20-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . ./
RUN npm run build

FROM alpine:3.20
COPY --from=build /app/build/ /opt/frontend_build/
CMD ["sh", "-c", "cp -r /opt/frontend_build/. /frontend_static/ && test -f /frontend_static/index.html"]
