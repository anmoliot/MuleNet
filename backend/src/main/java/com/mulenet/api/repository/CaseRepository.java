package com.mulenet.api.repository;

import com.mulenet.api.model.Case;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.Optional;

public interface CaseRepository extends JpaRepository<Case, Long> {
    Optional<Case> findByCaseId(String caseId);
    List<Case> findByStatus(Case.CaseStatus status);
    List<Case> findByComplaintId(String complaintId);
    List<Case> findAllByOrderByCreatedAtDesc();
}
