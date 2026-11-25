package com.mulenet.api.platform;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.mulenet.mlclient.model.ScoreRequest;
import com.mulenet.mlclient.model.ScoreResponse;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class ClientContractTest {
    @Test void generatedRequestPreservesFieldsAndLongTimestamps() throws Exception {
        ObjectMapper json = new ObjectMapper().findAndRegisterModules();
        ScoreRequest request = new ScoreRequest().accountId("a").asOf(4_000_000_000L)
            .snapshotId("a".repeat(64)).correlationId("contract-test");
        var document = json.readTree(json.writeValueAsString(request));
        assertEquals("a", document.path("account_id").asText());
        assertEquals(4_000_000_000L, document.path("as_of").asLong());
        assertEquals("contract-test", document.path("correlation_id").asText());
        assertEquals(4, document.size());
    }
}
