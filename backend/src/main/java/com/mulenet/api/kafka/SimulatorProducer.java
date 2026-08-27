package com.mulenet.api.kafka;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;
import java.util.Map;
import java.util.HashMap;
import java.time.Instant;

@Service
public class SimulatorProducer {
    private static final Logger logger = LoggerFactory.getLogger(SimulatorProducer.class);
    private static final String TOPIC = "mule-events";

    @Autowired
    private KafkaTemplate<String, Object> kafkaTemplate;

    public void produceTransaction(String sender, String receiver, double amount) {
        Map<String, Object> txn = new HashMap<>();
        txn.put("utr", "UTR" + System.currentTimeMillis());
        txn.put("sender_account", sender);
        txn.put("receiver_account", receiver);
        txn.put("amount", amount);
        txn.put("timestamp", Instant.now().toString());
        
        logger.info("Producing transaction to {}: {}", TOPIC, txn);
        kafkaTemplate.send(TOPIC, txn);
    }
}
