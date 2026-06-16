package com.mulenet.api.config;

import com.mulenet.api.model.User;
import com.mulenet.api.model.ExternalWatchlist;
import com.mulenet.api.repository.UserRepository;
import com.mulenet.api.repository.ExternalWatchlistRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.CommandLineRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

@Component
public class DataInitializer implements CommandLineRunner {

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private ExternalWatchlistRepository watchlistRepository;

    @Autowired
    private PasswordEncoder passwordEncoder;

    @Override
    public void run(String... args) throws Exception {
        // 1. Initializing Users
        if (userRepository.count() == 0) {
            userRepository.save(new User("investigator", passwordEncoder.encode("password"), User.Role.INVESTIGATOR));
            userRepository.save(new User("supervisor", passwordEncoder.encode("password"), User.Role.SUPERVISOR));
            userRepository.save(new User("admin", passwordEncoder.encode("password"), User.Role.FRAUD_ADMIN));
            userRepository.save(new User("compliance", passwordEncoder.encode("password"), User.Role.COMPLIANCE_OFFICER));
            System.out.println("[DataInitializer] Default security users initialized successfully.");
        }

        // 2. Initializing Watchlists
        if (watchlistRepository.count() == 0) {
            watchlistRepository.save(new ExternalWatchlist("AC-1199", "I4C_SUSPECT_REGISTRY", 25.0, "EXACT", 0.95, "Account found in I4C suspect database"));
            watchlistRepository.save(new ExternalWatchlist("AC-8102", "NCRP_FLAGGED", 30.0, "EXACT", 0.98, "Account flagged by NCRP cybercrime portal"));
            watchlistRepository.save(new ExternalWatchlist("AC-4455", "CONSORTIUM_BLACKLIST", 20.0, "EXACT", 0.85, "Flagged in inter-bank consortium fraud network"));
            watchlistRepository.save(new ExternalWatchlist("AC-9900", "FUZZY_WATCHLIST", 10.0, "FUZZY", 0.65, "Partial name/PAN match in regional watchlist"));
            watchlistRepository.save(new ExternalWatchlist("DEV-111", "DEVICE_BLACKLIST", 15.0, "DEVICE_LINKED", 0.90, "Associated device flagged for fraud operations"));
            watchlistRepository.save(new ExternalWatchlist("DEV-333", "DEVICE_BLACKLIST", 15.0, "DEVICE_LINKED", 0.90, "Associated device flagged for suspicious access velocity"));
            System.out.println("[DataInitializer] External threat intelligence database populated.");
        }
    }
}
