package com.mulenet.api.controller;

import com.mulenet.api.model.ExternalWatchlist;
import com.mulenet.api.repository.ExternalWatchlistRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.*;

@RestController
@RequestMapping("/api/external")
@CrossOrigin(origins = "*")
public class WatchlistController {

    @Autowired
    private ExternalWatchlistRepository watchlistRepository;

    @PostMapping("/watchlist")
    @PreAuthorize("hasAnyRole('INVESTIGATOR', 'SUPERVISOR', 'FRAUD_ADMIN', 'COMPLIANCE_OFFICER')")
    public ResponseEntity<List<ExternalWatchlist>> lookupWatchlist(@RequestBody Map<String, List<String>> payload) {
        List<String> accountIds = payload.getOrDefault("accountIds", Collections.emptyList());
        List<String> deviceIds = payload.getOrDefault("deviceIds", Collections.emptyList());

        List<String> queryIds = new ArrayList<>();
        queryIds.addAll(accountIds);
        queryIds.addAll(deviceIds);

        if (queryIds.isEmpty()) {
            return ResponseEntity.ok(Collections.emptyList());
        }

        List<ExternalWatchlist> hits = watchlistRepository.findByAccountIdIn(queryIds);
        return ResponseEntity.ok(hits);
    }

    @GetMapping("/watchlist/all")
    @PreAuthorize("hasAnyRole('INVESTIGATOR', 'SUPERVISOR', 'FRAUD_ADMIN', 'COMPLIANCE_OFFICER')")
    public ResponseEntity<List<ExternalWatchlist>> listAllWatchlist() {
        List<ExternalWatchlist> list = watchlistRepository.findAll();
        return ResponseEntity.ok(list);
    }

    @PostMapping("/watchlist/add")
    @PreAuthorize("hasRole('FRAUD_ADMIN')")
    public ResponseEntity<ExternalWatchlist> addWatchlist(@RequestBody ExternalWatchlist watchlist) {
        if (watchlist.getAccountId() == null || watchlist.getSource() == null) {
            return ResponseEntity.badRequest().build();
        }
        // Force calculation of iocType based on input
        watchlist.setAccountId(watchlist.getAccountId());
        ExternalWatchlist saved = watchlistRepository.save(watchlist);
        return ResponseEntity.ok(saved);
    }

    @DeleteMapping("/watchlist/remove/{id}")
    @PreAuthorize("hasRole('FRAUD_ADMIN')")
    public ResponseEntity<?> removeWatchlist(@PathVariable Long id) {
        return watchlistRepository.findById(id)
                .map(item -> {
                    watchlistRepository.delete(item);
                    return ResponseEntity.ok().build();
                })
                .orElse(ResponseEntity.notFound().build());
    }
}
