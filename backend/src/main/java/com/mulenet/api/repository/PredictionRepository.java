package com.mulenet.api.repository;

import com.mulenet.api.model.Prediction;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface PredictionRepository extends JpaRepository<Prediction, Long> {
    List<Prediction> findByAccountId(String accountId);
    List<Prediction> findByCaseId(String caseId);
}
