package com.mulenet.api.platform;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.jsonwebtoken.Claims;
import java.time.Duration;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.TimeUnit;
import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.apache.kafka.common.serialization.StringSerializer;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.config.ConcurrentKafkaListenerContainerFactory;
import org.springframework.kafka.config.TopicBuilder;
import org.springframework.kafka.core.*;
import org.springframework.kafka.listener.ContainerProperties;
import org.springframework.kafka.listener.DefaultErrorHandler;
import org.springframework.scheduling.annotation.*;
import org.springframework.util.backoff.FixedBackOff;

@Configuration("platformKafkaConfiguration")
@Profile("platform")
@EnableScheduling
public class PlatformKafka {
    @Bean
    public NewTopic ingestionTopic() { return TopicBuilder.name("mulenet.transactions").partitions(3).replicas(1).build(); }
    @Bean
    public NewTopic decisionsTopic() { return TopicBuilder.name("mulenet.decisions").partitions(3).replicas(1).build(); }
    @Bean
    public NewTopic dlqTopic() { return TopicBuilder.name("mulenet.transactions.dlq").partitions(3).replicas(1).build(); }

    @Bean("platformProducerFactory")
    public DefaultKafkaProducerFactory<String, String> producerFactory(@Value("${spring.kafka.bootstrap-servers}") String bootstrap) {
        Map<String, Object> properties = new HashMap<>();
        properties.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrap);
        properties.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class);
        properties.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, StringSerializer.class);
        properties.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, true);
        properties.put(ProducerConfig.ACKS_CONFIG, "all");
        properties.put(ProducerConfig.DELIVERY_TIMEOUT_MS_CONFIG, 10000);
        properties.put(ProducerConfig.REQUEST_TIMEOUT_MS_CONFIG, 5000);
        return new DefaultKafkaProducerFactory<>(properties);
    }

    @Bean("platformKafka")
    public KafkaTemplate<String, String> template(@Qualifier("platformProducerFactory") DefaultKafkaProducerFactory<String, String> factory) {
        return new KafkaTemplate<>(factory);
    }

    @Bean("platformListener")
    public ConcurrentKafkaListenerContainerFactory<String, String> listener(
            @Value("${spring.kafka.bootstrap-servers}") String bootstrap,
            @Qualifier("platformKafka") KafkaTemplate<String, String> kafka, PrivacyCodec privacy, ObjectMapper mapper) {
        Map<String, Object> properties = new HashMap<>();
        properties.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrap);
        properties.put(ConsumerConfig.GROUP_ID_CONFIG, "mulenet-platform-v1");
        properties.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class);
        properties.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class);
        properties.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, false);
        properties.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");
        properties.put(ConsumerConfig.ISOLATION_LEVEL_CONFIG, "read_committed");
        properties.put(ConsumerConfig.MAX_POLL_RECORDS_CONFIG, 1);
        properties.put(ConsumerConfig.MAX_POLL_INTERVAL_MS_CONFIG, 120000);
        var factory = new ConcurrentKafkaListenerContainerFactory<String, String>();
        factory.setConsumerFactory(new DefaultKafkaConsumerFactory<>(properties));
        factory.getContainerProperties().setAckMode(ContainerProperties.AckMode.RECORD);
        var handler = new DefaultErrorHandler((record, exception) -> {
            try {
                String payload = String.valueOf(record.value());
                String sourceKey = String.valueOf(record.key());
                String receipt = mapper.writeValueAsString(Map.of("id", UUID.randomUUID().toString(),
                    "source_topic", record.topic(), "source_partition", record.partition(), "source_offset", record.offset(),
                    "payload_sha256", PrivacyCodec.hash(payload), "key_sha256", PrivacyCodec.hash(sourceKey),
                    "encrypted_payload", privacy.encrypt("dlq", payload.substring(0, Math.min(4096, payload.length()))),
                    "payload_truncated", payload.length() > 4096,
                    "error", exception.getClass().getSimpleName()));
                kafka.send("mulenet.transactions.dlq", record.partition(), PrivacyCodec.hash(sourceKey), receipt).get(10, TimeUnit.SECONDS);
            } catch (Exception failure) { throw new IllegalStateException("DLQ publish failed; input is not acknowledged", failure); }
        }, new FixedBackOff(100, 2));
        handler.setAckAfterHandle(true);
        factory.setCommonErrorHandler(handler);
        return factory;
    }

    @Bean
    public Worker platformWorker(PlatformService platform, ServiceTokens tokens, ObjectMapper mapper,
                                  JdbcTemplate db, @Qualifier("platformKafka") KafkaTemplate<String, String> kafka) {
        return new Worker(platform, tokens, mapper, db, kafka);
    }

    public static class Worker {
        private final PlatformService platform;
        private final ServiceTokens tokens;
        private final ObjectMapper mapper;
        private final JdbcTemplate db;
        private final KafkaTemplate<String, String> kafka;
        public Worker(PlatformService platform, ServiceTokens tokens, ObjectMapper mapper, JdbcTemplate db, KafkaTemplate<String, String> kafka) {
            this.platform = platform; this.tokens = tokens; this.mapper = mapper; this.db = db; this.kafka = kafka;
        }
        @KafkaListener(topics = "mulenet.transactions", containerFactory = "platformListener", autoStartup = "${mulenet.kafka.enabled:true}")
        public void consume(ConsumerRecord<String, String> record) throws Exception {
            Claims claims = tokens.verifyIngestion(record.value());
            String tenant = claims.get("tenant", String.class);
            if (tenant == null || !tenant.matches("[a-zA-Z0-9_-]{1,64}")) throw new IllegalArgumentException("Invalid ingestion tenant");
            var event = mapper.readTree(claims.get("body", String.class));
            if (!String.valueOf(record.key()).equals(tenant + ":" + event.path("source").asText()))
                throw new IllegalArgumentException("Partition key must be tenant and source account ID");
            platform.process(tenant, event, UUID.nameUUIDFromBytes(claims.getId().getBytes(java.nio.charset.StandardCharsets.UTF_8)).toString());
        }

        @Scheduled(fixedDelayString = "${mulenet.outbox.delay-ms:100}")
        public void publish() {
            for (Map<String, Object> row : db.queryForList("SELECT id,event_id,tenant,partition_key,kind,payload FROM platform_outbox WHERE published=FALSE ORDER BY id LIMIT 50")) {
                try {
                    String topic = row.get("kind").equals("ingestion") ? "mulenet.transactions" : "mulenet.decisions";
                    kafka.send(topic, (String) row.get("partition_key"), (String) row.get("payload")).get(10, TimeUnit.SECONDS);
                    db.update("UPDATE platform_outbox SET published=TRUE WHERE id=?", row.get("id"));
                } catch (Exception failure) {
                    // Retain pending rows on failure. Do not leak signed tokens or event bodies into logs.
                    return;
                }
            }
        }

        @Scheduled(fixedDelay = 1000)
        public void release() { platform.releaseExpired(); }
    }
}
