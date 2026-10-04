FROM node:24-bookworm AS web
ARG API_URL=""
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm test -- --watch=false && npx ng build --define "API_URL='${API_URL}'"

FROM maven:3.9-eclipse-temurin-25 AS api
WORKDIR /api
COPY backend/pom.xml ./
RUN mvn -q dependency:go-offline
COPY backend/src src
COPY --from=web /web/dist/frontend/browser src/main/resources/static
RUN mvn -q package

# glibc base: OpenCV and ONNX Runtime natives need it
FROM eclipse-temurin:25-jre
WORKDIR /app
COPY --from=api /api/target/optiframe-api-*.jar app.jar
COPY backend/models models
# Second guard behind the Java header check: OpenCV refuses to decode bigger images.
ENV OPENCV_IO_MAX_IMAGE_PIXELS=30000000
# OpenCV loads its native lib into the temp dir, so it needs a writable home but nothing else.
RUN useradd --system --create-home --uid 10001 app
USER app
EXPOSE 8080
# Images live in native memory (OpenCV Mats), outside the heap: leave them room.
ENTRYPOINT ["java", "-XX:MaxRAMPercentage=50", "-jar", "app.jar"]
