package com.mulenet.api.controller;

import com.mulenet.api.model.User;
import com.mulenet.api.model.AuditLog;
import com.mulenet.api.repository.UserRepository;
import com.mulenet.api.repository.AuditLogRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/users")
@CrossOrigin(origins = "*")
public class UserController {

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private AuditLogRepository auditLogRepository;

    private String getUsername() {
        return SecurityContextHolder.getContext().getAuthentication().getName();
    }

    private String getRole() {
        return SecurityContextHolder.getContext().getAuthentication().getAuthorities().stream()
                .map(a -> a.getAuthority().replace("ROLE_", ""))
                .findFirst().orElse("UNKNOWN");
    }

    /**
     * GET /api/users — list all users
     */
    @GetMapping
    @PreAuthorize("hasRole('FRAUD_ADMIN')")
    public ResponseEntity<List<User>> listUsers() {
        List<User> users = userRepository.findAll();
        // Remove password hash from response for security
        users.forEach(u -> u.setPassword(null));
        return ResponseEntity.ok(users);
    }

    /**
     * PUT /api/users/{username}/status — toggle active status of a user
     */
    @PutMapping("/{username}/status")
    @PreAuthorize("hasRole('FRAUD_ADMIN')")
    public ResponseEntity<?> toggleUserStatus(
            @PathVariable String username,
            @RequestBody Map<String, Boolean> body) {

        if (getUsername().equalsIgnoreCase(username)) {
            return ResponseEntity.badRequest().body(Map.of("message", "Cannot toggle status of your own account"));
        }

        return userRepository.findByUsername(username)
                .map(user -> {
                    Boolean active = body.get("isActive");
                    if (active == null) {
                        return ResponseEntity.badRequest().body(Map.of("message", "isActive parameter is required"));
                    }
                    user.setIsActive(active);
                    userRepository.save(user);

                    // Audit user status change
                    auditLogRepository.save(new AuditLog(
                            getUsername(),
                            getRole(),
                            "USER_STATUS_TOGGLE",
                            "Toggled user '" + username + "' active status to: " + active,
                            null
                    ));

                    // Clear password hash before returning
                    user.setPassword(null);
                    return ResponseEntity.ok(user);
                })
                .orElse(ResponseEntity.notFound().build());
    }
}
