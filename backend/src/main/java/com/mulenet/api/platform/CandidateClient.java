package com.mulenet.api.platform;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.mulenet.mlclient.ApiClient;
import com.mulenet.mlclient.api.DefaultApi;
import com.mulenet.mlclient.model.ScoreRequest;
import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.circuitbreaker.CircuitBreakerConfig;
import io.github.resilience4j.core.IntervalFunction;
import io.github.resilience4j.retry.Retry;
import io.github.resilience4j.retry.RetryConfig;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Profile;
import org.springframework.http.*;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.client.HttpStatusCodeException;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestTemplate;

@Service
@Profile("platform")
public class CandidateClient {
    private final ServiceTokens tokens;
    private final ObjectMapper mapper;
    private final String baseUrl;
    private final RestTemplate transport;
    private final CircuitBreaker circuit;
    private final Retry retry;

    public CandidateClient(ServiceTokens tokens, ObjectMapper mapper,
                           @Value("${mulenet.ml-url}") String baseUrl) {
        this.tokens = tokens;
        this.mapper = mapper;
        this.baseUrl = baseUrl;
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(300);
        factory.setReadTimeout(1500);
        transport = new RestTemplate(factory);
        circuit = CircuitBreaker.of("ml", CircuitBreakerConfig.custom().slidingWindowSize(10)
            .minimumNumberOfCalls(3).failureRateThreshold(50).waitDurationInOpenState(Duration.ofSeconds(30)).build());
        retry = Retry.of("ml", RetryConfig.custom().maxAttempts(2)
            .intervalFunction(IntervalFunction.ofExponentialRandomBackoff(30, 2, .5))
            .retryOnException(e -> e instanceof ResourceAccessException ||
                (e instanceof HttpStatusCodeException status && status.getStatusCode().is5xxServerError())).build());
    }

    public JsonNode score(String tenant, String accountId, long asOf, String correlationId,
                          long completeFrom, List<JsonNode> events) {
        return circuit.executeSupplier(() -> retry.executeSupplier(() -> {
            String credential = tokens.ml(tenant);
            HttpHeaders headers = new HttpHeaders();
            headers.setBearerAuth(credential);
            headers.setContentType(MediaType.APPLICATION_JSON);
            Map<String, Object> snapshot = Map.of("complete_from", completeFrom, "watermark", asOf,
                "events", events, "accounts", List.of());
            JsonNode receipt = transport.postForObject(baseUrl + "/v1/snapshots", new HttpEntity<>(snapshot, headers), JsonNode.class);
            if (receipt == null || !receipt.path("snapshot_id").asText().matches("[a-f0-9]{64}"))
                throw new IllegalStateException("Invalid ML snapshot receipt");
            ApiClient apiClient = new ApiClient(transport);
            apiClient.setBasePath(baseUrl);
            apiClient.setBearerToken(credential);
            ScoreRequest request = new ScoreRequest().accountId(accountId).asOf(asOf)
                .snapshotId(receipt.path("snapshot_id").asText()).correlationId(correlationId);
            JsonNode result = mapper.valueToTree(new DefaultApi(apiClient).score(request));
            if (!result.path("probability").isNumber() || !Double.isFinite(result.path("probability").asDouble()) ||
                result.path("probability").asDouble() < 0 || result.path("probability").asDouble() > 1 ||
                !accountId.equals(result.path("account_id").asText()) || result.path("as_of").asLong() != asOf ||
                result.path("model_version").asText().isBlank() || result.path("feature_schema_hash").asText().length() != 64)
                throw new IllegalStateException("ML response contract mismatch");
            return result;
        }));
    }

    public String circuitState() { return circuit.getState().name(); }
}
