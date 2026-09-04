package com.mulenet.api.controller;

import com.mulenet.api.config.DataSeeder;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/demo")
@CrossOrigin(origins = "*")
public class DemoController {

    @Autowired
    private DataSeeder dataSeeder;

    @PostMapping("/seed")
    public ResponseEntity<?> seedDemo() {
        dataSeeder.seedWatchlist();
        dataSeeder.seedCases();
        return ResponseEntity.ok(Map.of("status", "success", "message", "Demo cases and watchlist seeded successfully"));
    }
}
