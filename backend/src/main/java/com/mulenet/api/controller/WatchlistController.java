package com.mulenet.api.controller;

import com.mulenet.api.model.ExternalWatchlist;
import com.mulenet.api.repository.ExternalWatchlistRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.*;

@RestController
@RequestMapping("/api/external")
@CrossOrigin(origins = "*")
public class WatchlistController {

    @Autowired
    private ExternalWatchlistRepository watchlistRepository;

    @PostMapping("/watchlist")
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
}
