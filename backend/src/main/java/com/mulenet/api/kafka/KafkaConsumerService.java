package com.mulenet.api.kafka;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.mulenet.api.dto.IntakeRequest;
import com.mulenet.api.model.Complaint;
import com.mulenet.api.model.Transaction;
import com.mulenet.api.model.Case;
import com.mulenet.api.repository.ComplaintRepository;
import com.mulenet.api.repository.TransactionRepository;
import com.mulenet.api.service.MlService;
import com.mulenet.api.service.PolicyEngine;
import com.mulenet.api.service.NotificationService;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.support.Acknowledgment;
import org.springframework.stereotype.Service;

import java.util.Collections;
import java.util.Map;

@Service
public class KafkaConsumerService {

    private static final Logger logger = LoggerFactory.getLogger(KafkaConsumerService.class);

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private ComplaintRepository complaintRepository;

    @Autowired
    private TransactionRepository transactionRepository;

    @Autowired
    private MlService mlService;

    @Autowired
    private PolicyEngine policyEngine;

    @Autowired
    private NotificationService notificationService;

    @KafkaListener(topics = "mule-events", groupId = "mulenet-backend-group")
    public void consumeTransaction(ConsumerRecord<String, String> record, Acknowledgment acknowledgment) {
        try {
            logger.info("Received Kafka message on topic mule-events: {}", record.value());
            Map<String, Object> txnMap = objectMapper.readValue(record.value(), Map.class);
            
            String utr = (String) txnMap.get("utr");
            String sender = (String) txnMap.get("sender_account");
            String receiver = (String) txnMap.get("receiver_account");
            double amount = Double.parseDouble(txnMap.get("amount").toString());
            String timestamp = (String) txnMap.get("timestamp");
            String deviceId = (String) txnMap.getOrDefault("device_id", "UNKNOWN");

            // Build Complaint and Transaction
            Complaint complaint = new Complaint();
            complaint.setComplaintId("KAFKA-" + utr);
            complaint.setUtr(utr);
            complaint.setAmount(amount);
            complaint.setFirstBeneficiary(receiver);

            Transaction transaction = new Transaction();
            transaction.setUtr(utr);
            transaction.setSenderAccount(sender);
            transaction.setReceiverAccount(receiver);
            transaction.setAmount(amount);
            transaction.setTimestamp(timestamp);
            transaction.setDeviceId(deviceId);

            IntakeRequest intakeRequest = new IntakeRequest(complaint, Collections.singletonList(transaction));
            
            // Save initial data
            complaintRepository.save(complaint);
            transactionRepository.save(transaction);

            // Call ML Service
            String mlResponse = mlService.analyzeGraph(intakeRequest);

            // Process via PolicyEngine (creates Case/Alert)
            Case fraudCase = policyEngine.processAnalysis(mlResponse, complaint.getComplaintId());
            
            // Broadcast via SSE
            notificationService.broadcastStreamEvent(txnMap, fraudCase);
            
            logger.info("Successfully processed Kafka event into Case: {}, Risk: {}", fraudCase.getCaseId(), fraudCase.getRiskScore());

            // Acknowledge the message
            acknowledgment.acknowledge();
        } catch (Exception e) {
            logger.error("Error processing Kafka message: ", e);
            // Decide on DLQ or manual retry. Acknowledging anyway to avoid poison pills in this demo.
            acknowledgment.acknowledge();
        }
    }
}
