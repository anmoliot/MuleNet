package com.mulenet.api.controller;

import com.mulenet.api.config.JwtUtil;
import com.mulenet.api.model.User;
import com.mulenet.api.repository.UserRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

@RestController
@RequestMapping("/api/auth")
@CrossOrigin(origins = "*")
public class AuthController {

    private static final Logger logger = LoggerFactory.getLogger(AuthController.class);

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private PasswordEncoder passwordEncoder;

    @Autowired
    private JwtUtil jwtUtil;

    @PostMapping("/login")
    public ResponseEntity<?> login(@RequestBody Map<String, String> request) {
        String username = request.get("username");
        String password = request.get("password");

        if (username == null || password == null) {
            logger.warn("Login attempt rejected: missing username or password payload parameters.");
            return ResponseEntity.badRequest().body(Map.of("error", "Username and password are required"));
        }

        Optional<User> userOpt = userRepository.findByUsername(username);

        if (userOpt.isPresent() && passwordEncoder.matches(password, userOpt.get().getPassword())) {
            User user = userOpt.get();
            if (!user.getIsActive()) {
                logger.warn("Login attempt blocked for inactive user: {}", username);
                return ResponseEntity.status(HttpStatus.FORBIDDEN).body(Map.of("error", "User account is inactive. Please contact administrator."));
            }
            logger.info("User authenticated successfully: {} with role: {}", username, user.getRole().name());
            String token = jwtUtil.generateToken(user.getUsername(), user.getRole().name());

            Map<String, Object> response = new HashMap<>();
            response.put("token", token);
            response.put("username", user.getUsername());
            response.put("role", user.getRole().name());
            return ResponseEntity.ok(response);
        }

        logger.warn("Failed login credentials attempt for username: {}", username);
        return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(Map.of("error", "Invalid username or password"));
    }
}
