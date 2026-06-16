package com.mulenet.api.repository;

import com.mulenet.api.model.ExternalWatchlist;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface ExternalWatchlistRepository extends JpaRepository<ExternalWatchlist, Long> {
    List<ExternalWatchlist> findByAccountIdIn(List<String> accountIds);
}
