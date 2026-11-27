package com.mulenet.api.platform;

import java.nio.file.Path;
import java.time.Duration;
import java.util.*;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.*;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.images.builder.Transferable;
import org.testcontainers.kafka.KafkaContainer;
import org.testcontainers.utility.DockerImageName;

@org.springframework.boot.test.autoconfigure.actuate.observability.AutoConfigureObservability(tracing = false)
abstract class PlatformTestStack {
    static final Network NETWORK = Network.newNetwork();
    static final String SERVICE_SECRET = UUID.randomUUID().toString() + UUID.randomUUID();
    static final String STREAM_SECRET = UUID.randomUUID().toString() + UUID.randomUUID();
    static final String INGESTION_SECRET = UUID.randomUUID().toString() + UUID.randomUUID();
    static final String KEY = Base64.getEncoder().encodeToString(java.security.SecureRandom.getSeed(32));
    static final String RUNTIME_PASSWORD = UUID.randomUUID().toString();
    static final Map<String, String> PASSWORDS = Map.of("analyst", UUID.randomUUID().toString(), "supervisor", UUID.randomUUID().toString(), "admin", UUID.randomUUID().toString(), "auditor", UUID.randomUUID().toString());
    static final String INIT_SQL = "CREATE ROLE mulenet_runtime LOGIN PASSWORD '" + RUNTIME_PASSWORD + "'; GRANT USAGE ON SCHEMA public TO mulenet_runtime; ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT,INSERT,UPDATE,DELETE ON TABLES TO mulenet_runtime; ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE,SELECT ON SEQUENCES TO mulenet_runtime;";
    @Container static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:17.7-alpine")
        .withDatabaseName("mulenet").withUsername("migration").withPassword(UUID.randomUUID().toString())
        .withCopyToContainer(Transferable.of(INIT_SQL), "/docker-entrypoint-initdb.d/10-runtime.sql").withNetwork(NETWORK);
    @Container static KafkaContainer kafka = new KafkaContainer(DockerImageName.parse("apache/kafka:4.1.1")).withNetwork(NETWORK);
    @Container static GenericContainer<?> redis = new GenericContainer<>("redis:7.4.7-alpine").withExposedPorts(6379).withNetwork(NETWORK).withNetworkAliases("redis");
    @Container static GenericContainer<?> ml = new GenericContainer<>(System.getenv().getOrDefault("MULENET_ML_TEST_IMAGE", "mulenet/ml:local"))
        .withNetwork(NETWORK).dependsOn(redis).withExposedPorts(8000)
        .withFileSystemBind(Path.of(System.getenv().getOrDefault("MULENET_TEST_MODEL_DIR", "../artifacts/demo-temporal-v3")).toAbsolutePath().normalize().toString(), "/models", BindMode.READ_ONLY)
        .withEnv("MULENET_MODEL_DIR", "/models").withEnv("MULENET_ALLOW_SYNTHETIC", "true")
        .withEnv("MULENET_SERVICE_SECRET", SERVICE_SECRET).withEnv("MULENET_REDIS_URL", "redis://redis:6379/0")
        .waitingFor(org.testcontainers.containers.wait.strategy.Wait.forHttp("/health").forPort(8000)).withStartupTimeout(Duration.ofMinutes(2));

    @DynamicPropertySource static void properties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", () -> "mulenet_runtime");
        registry.add("spring.datasource.password", () -> RUNTIME_PASSWORD);
        registry.add("spring.datasource.driverClassName", () -> "org.postgresql.Driver");
        registry.add("spring.jpa.properties.hibernate.dialect", () -> "org.hibernate.dialect.PostgreSQLDialect");
        registry.add("spring.jpa.hibernate.ddl-auto", () -> "validate");
        registry.add("spring.flyway.enabled", () -> true);
        registry.add("spring.flyway.user", postgres::getUsername);
        registry.add("spring.flyway.password", postgres::getPassword);
        registry.add("spring.kafka.bootstrap-servers", kafka::getBootstrapServers);
        registry.add("mulenet.token-key", () -> KEY);
        registry.add("mulenet.encryption-key", () -> KEY);
        registry.add("mulenet.service-secret", () -> SERVICE_SECRET);
        registry.add("mulenet.stream-secret", () -> STREAM_SECRET);
        registry.add("mulenet.ingestion-secret", () -> INGESTION_SECRET);
        registry.add("mulenet.ml-url", () -> "http://" + ml.getHost() + ":" + ml.getMappedPort(8000));
        registry.add("mulenet.demo-jwt-secret", () -> KEY);
        PASSWORDS.forEach((role, password) -> registry.add("mulenet.demo-passwords." + role, () -> password));
    }

}
