package com.mulenet.api.repository;

import com.mulenet.api.model.PolicyConfig;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface PolicyConfigRepository extends JpaRepository<PolicyConfig, String> {
}
