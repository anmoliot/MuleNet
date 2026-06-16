package com.mulenet.api.repository;

import com.mulenet.api.model.InvestigatorAction;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface InvestigatorActionRepository extends JpaRepository<InvestigatorAction, Long> {
    List<InvestigatorAction> findByCaseIdOrderByTimestampDesc(String caseId);
    List<InvestigatorAction> findByAccountId(String accountId);
}
