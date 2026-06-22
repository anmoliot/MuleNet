package com.mulenet.api.config;

import com.mulenet.api.model.User;
import com.mulenet.api.model.ExternalWatchlist;
import com.mulenet.api.repository.UserRepository;
import com.mulenet.api.repository.ExternalWatchlistRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.CommandLineRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

import java.util.UUID;

@Component
public class DataInitializer implements CommandLineRunner {

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private ExternalWatchlistRepository watchlistRepository;

    @Autowired
    private PasswordEncoder passwordEncoder;

    @Value("${spring.profiles.active:}")
    private String activeProfiles;

    @Value("${BOOTSTRAP_INVESTIGATOR_PASSWORD:password}")
    private String investigatorPassword;

    @Value("${BOOTSTRAP_SUPERVISOR_PASSWORD:password}")
    private String supervisorPassword;

    @Value("${BOOTSTRAP_ADMIN_PASSWORD:password}")
    private String adminPassword;

    @Value("${BOOTSTRAP_COMPLIANCE_PASSWORD:password}")
    private String compliancePassword;

    @Override
    public void run(String... args) throws Exception {
        boolean isProd = activeProfiles != null && activeProfiles.contains("prod");

        // 1. Initializing Users individually
        seedUser("investigator", investigatorPassword, User.Role.INVESTIGATOR, isProd);
        seedUser("supervisor", supervisorPassword, User.Role.SUPERVISOR, isProd);
        seedUser("admin", adminPassword, User.Role.FRAUD_ADMIN, isProd);
        seedUser("compliance", compliancePassword, User.Role.COMPLIANCE_OFFICER, isProd);

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

    private void seedUser(String username, String rawPassword, User.Role role, boolean isProd) {
        userRepository.findByUsername(username).ifPresentOrElse(
            user -> {
                // If user exists but has a blank password, set it securely
                if (user.getPassword() == null || user.getPassword().trim().isEmpty()) {
                    String passwordToUse = rawPassword;
                    if (isProd && "password".equals(rawPassword)) {
                        passwordToUse = UUID.randomUUID().toString();
                        System.err.println("====================================================");
                        System.err.println("WARNING: Repairing missing password for existing user '" + username + "' in production!");
                        System.err.println("Generated secure bootstrap credential: " + username + " / " + passwordToUse);
                        System.err.println("====================================================");
                    }
                    user.setPassword(passwordEncoder.encode(passwordToUse));
                    userRepository.save(user);
                    System.out.println("[DataInitializer] Securely updated password for existing user: " + username);
                }
            },
            () -> {
                // If user does not exist, seed them securely
                String passwordToUse = rawPassword;
                if (isProd && "password".equals(rawPassword)) {
                    passwordToUse = UUID.randomUUID().toString();
                    System.err.println("====================================================");
                    System.err.println("WARNING: Bootstrapping new user '" + username + "' in production with default settings!");
                    System.err.println("Generated secure bootstrap credential: " + username + " / " + passwordToUse);
                    System.err.println("====================================================");
                }
                userRepository.save(new User(username, passwordEncoder.encode(passwordToUse), role));
                System.out.println("[DataInitializer] Securely created default user: " + username + " (" + role.name() + ")");
            }
        );
    }
}
