# Build stage
FROM maven:3.9.9-eclipse-temurin-17 AS build
WORKDIR /app/backend
COPY backend/pom.xml .
COPY backend/src ./src
COPY contracts /app/contracts
RUN --mount=type=cache,target=/root/.m2 mvn -B -ntp clean package -DskipTests

# Run stage
FROM eclipse-temurin:17-jre-alpine
WORKDIR /app
COPY --from=build /app/backend/target/*.jar app.jar
RUN addgroup -g 10001 app && adduser -D -u 10001 -G app app
USER 10001
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
