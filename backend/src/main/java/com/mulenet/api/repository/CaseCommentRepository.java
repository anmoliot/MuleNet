package com.mulenet.api.repository;

import com.mulenet.api.model.CaseComment;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface CaseCommentRepository extends JpaRepository<CaseComment, Long> {
    List<CaseComment> findByCaseIdOrderByCreatedAtAsc(String caseId);
}
