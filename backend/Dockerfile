# Build stage
FROM maven:3.9.9-eclipse-temurin-17@sha256:f58d59b6273e785ac0a4477f6e9b5ba1d7731c75b906c0f7b34076f1851318cc AS build
WORKDIR /app/backend
COPY backend/pom.xml .
COPY backend/src ./src
COPY contracts /app/contracts
RUN --mount=type=cache,target=/root/.m2 mvn -B -ntp clean package -DskipTests

# Run stage
FROM eclipse-temurin:17-jre-alpine@sha256:2b4113ae80e31f103b284dd3bc3e008add670cf8555417b5b289fa1128f2f0a3
WORKDIR /app
RUN apk upgrade --no-cache
COPY --from=build /app/backend/target/*.jar app.jar
RUN addgroup -g 10001 app && adduser -D -u 10001 -G app app
USER 10001
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
