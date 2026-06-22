package com.mulenet.api.repository;

import com.mulenet.api.model.Alert;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface AlertRepository extends JpaRepository<Alert, Long> {
    Optional<Alert> findByAlertId(String alertId);
    List<Alert> findByAccountId(String accountId);
    List<Alert> findByStatus(String status);
}
