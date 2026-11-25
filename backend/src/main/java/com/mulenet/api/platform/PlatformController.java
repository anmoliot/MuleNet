package com.mulenet.api.platform;

import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import java.util.*;
import org.springframework.context.annotation.Profile;
import org.springframework.http.HttpStatus;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

@RestController
@Profile("platform")
@RequestMapping("/api/v1")
public class PlatformController {
    private final PlatformService platform;
    private final PrivacyCodec privacy;
    public PlatformController(PlatformService platform, PrivacyCodec privacy) { this.platform = platform; this.privacy = privacy; }

    static String tenant(Authentication authentication) {
        if (!(authentication instanceof JwtAuthenticationToken jwt)) throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "OIDC bearer required");
        String tenant = jwt.getToken().getClaimAsString("tenant");
        if (tenant == null || !tenant.matches("[a-zA-Z0-9_-]{1,64}")) throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Tenant claim required");
        return tenant;
    }
    private String actor(Authentication auth) { return privacy.token(tenant(auth), "actor", auth.getName()); }

    public record Ingest(@NotEmpty @Size(max = 100) List<@Valid Payment> transactions) {}
    public record PolicyChange(@Min(1) int expectedVersion, @NotNull @Valid ReviewPolicy config,
                               @NotBlank @Size(min = 10, max = 2000) String rationale) {}
    public record CaseAction(@Min(1) int expectedVersion,
                             @NotBlank @Size(min = 10, max = 2000) String rationale,
                             @Size(max = 128) @Pattern(regexp = "[a-zA-Z0-9_-]+") String assignee) {}
    public record Feedback(@NotNull Boolean fraudulent, @NotBlank @Size(min = 20, max = 4000) String evidence) {}
    public record Replay(@NotBlank @Size(min = 10, max = 2000) String rationale) {}

    @PostMapping("/transactions")
    @ResponseStatus(HttpStatus.ACCEPTED)
    @PreAuthorize("hasAnyRole('ANALYST','SUPERVISOR','ADMIN')")
    public Map<String, Object> ingest(@Valid @RequestBody Ingest request, Authentication auth) {
        return Map.of("transaction_ids", platform.enqueue(tenant(auth), actor(auth), request.transactions()), "state", "durably_queued", "external_intervention", false);
    }
    @GetMapping("/decisions")
    @PreAuthorize("hasAnyRole('ANALYST','SUPERVISOR','ADMIN','AUDITOR')")
    public List<Map<String, Object>> decisions(Authentication auth) { return platform.decisions(tenant(auth)); }
    @GetMapping("/decisions/{id}")
    @PreAuthorize("hasAnyRole('ANALYST','SUPERVISOR','ADMIN','AUDITOR')")
    public Map<String, Object> decision(@PathVariable String id, Authentication auth) { return platform.decision(tenant(auth), id); }
    @GetMapping("/policy")
    @PreAuthorize("hasAnyRole('ANALYST','SUPERVISOR','ADMIN','AUDITOR')")
    public Map<String, Object> policy(Authentication auth) { return platform.policy(tenant(auth)); }
    @PutMapping("/policy")
    @PreAuthorize("hasRole('ADMIN')")
    public Map<String, Object> policy(@Valid @RequestBody PolicyChange change, Authentication auth) {
        return platform.changePolicy(tenant(auth), actor(auth), change.expectedVersion(), change.config(), change.rationale());
    }
    @PostMapping("/decisions/{id}/notes")
    @PreAuthorize("hasAnyRole('ANALYST','SUPERVISOR','ADMIN')")
    public Map<String, Object> note(@PathVariable String id, @Valid @RequestBody CaseAction request, Authentication auth) {
        return platform.act(tenant(auth), actor(auth), id, request.expectedVersion(), "NOTE", request.rationale(), null);
    }
    @GetMapping("/decisions/{id}/notes")
    @PreAuthorize("hasAnyRole('ANALYST','SUPERVISOR','ADMIN','AUDITOR')")
    public List<Map<String, Object>> notes(@PathVariable String id, Authentication auth) { return platform.notes(tenant(auth), id); }
    @PostMapping("/decisions/{id}/feedback")
    @PreAuthorize("hasAnyRole('ANALYST','SUPERVISOR','ADMIN')")
    public void feedback(@PathVariable String id, @Valid @RequestBody Feedback request, Authentication auth) {
        String role = auth.getAuthorities().stream().map(a -> a.getAuthority().replace("ROLE_", "")).filter(r -> Set.of("SUPERVISOR", "ADMIN").contains(r)).findFirst().orElse("ANALYST");
        platform.feedback(tenant(auth), actor(auth), id, request.fraudulent(), request.evidence(), role);
    }
    @GetMapping("/feedback/export")
    @PreAuthorize("hasRole('ADMIN')")
    public List<Map<String, Object>> feedbackExport(Authentication auth) { return platform.feedbackExport(tenant(auth)); }
    @PostMapping("/replay/{transactionId}")
    @PreAuthorize("hasRole('ADMIN')")
    public void replay(@PathVariable String transactionId, @Valid @RequestBody Replay request, Authentication auth) {
        platform.replay(tenant(auth), actor(auth), transactionId, request.rationale());
    }
    @PostMapping("/decisions/{id}/appeal")
    @PreAuthorize("hasAnyRole('ANALYST','SUPERVISOR','ADMIN')")
    public Map<String, Object> appeal(@PathVariable String id, @Valid @RequestBody CaseAction request, Authentication auth) {
        return platform.act(tenant(auth), actor(auth), id, request.expectedVersion(), "APPEAL", request.rationale(), null);
    }
    @PostMapping("/decisions/{id}/actions/{action}")
    @PreAuthorize("hasAnyRole('SUPERVISOR','ADMIN')")
    public Map<String, Object> action(@PathVariable String id, @PathVariable String action, @Valid @RequestBody CaseAction request, Authentication auth) {
        if (!Set.of("APPROVE", "REJECT", "RELEASE", "ASSIGN").contains(action.toUpperCase(Locale.ROOT)))
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Unknown action");
        return platform.act(tenant(auth), actor(auth), id, request.expectedVersion(), action.toUpperCase(Locale.ROOT), request.rationale(), privacy.token(tenant(auth), "actor", request.assignee()));
    }
    @GetMapping("/audit")
    @PreAuthorize("hasAnyRole('SUPERVISOR','ADMIN','AUDITOR')")
    public List<Map<String, Object>> audit(Authentication auth, @RequestParam(defaultValue = "0") long after, @RequestParam(defaultValue = "50") int limit) {
        if (after < 0 || limit < 1 || limit > 100) throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, "Invalid audit page bounds");
        return platform.auditEntries(tenant(auth), after, limit);
    }
    @GetMapping("/health")
    @PreAuthorize("hasAnyRole('ANALYST','SUPERVISOR','ADMIN','AUDITOR')")
    public Map<String, Object> health(Authentication auth) {
        return Map.of("ml_circuit", platform.circuitState(), "tenant", tenant(auth), "production_approved", false);
    }
    @GetMapping("/decisions/{id}/str-draft")
    @PreAuthorize("hasAnyRole('SUPERVISOR','ADMIN','AUDITOR')")
    public Map<String, Object> draft(@PathVariable String id, Authentication auth) {
        return Map.of("document_type", "FIU-IND-style STR DRAFT TEMPLATE", "not_submitted", true,
            "regulatory_conformance_verified", false, "decision", platform.decision(tenant(auth), id));
    }
}
