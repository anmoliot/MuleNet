package com.mulenet.api.controller;

import com.mulenet.api.model.AuditLog;
import com.mulenet.api.repository.AuditLogRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/audit-logs")
@CrossOrigin(origins = "*")
public class AuditController {

    @Autowired
    private AuditLogRepository auditLogRepository;

    @GetMapping
    @PreAuthorize("hasAnyRole('SUPERVISOR', 'COMPLIANCE_OFFICER')")
    public ResponseEntity<List<AuditLog>> getAuditLogs() {
        List<AuditLog> logs = auditLogRepository.findAllByOrderByTimestampDesc();
        return ResponseEntity.ok(logs);
    }

    @GetMapping("/export/csv")
    @PreAuthorize("hasAnyRole('SUPERVISOR', 'COMPLIANCE_OFFICER')")
    public ResponseEntity<String> exportAuditLogsCsv() {
        List<AuditLog> logs = auditLogRepository.findAllByOrderByTimestampDesc();
        StringBuilder csv = new StringBuilder();
        csv.append("Timestamp,Actor,Role,Action,Target Entity,Details,IP Address,Success\n");
        for (AuditLog log : logs) {
            csv.append(log.getTimestamp() != null ? log.getTimestamp().toString() : "").append(",")
               .append(escapeCsv(log.getActor())).append(",")
               .append(escapeCsv(log.getRole())).append(",")
               .append(escapeCsv(log.getAction())).append(",")
               .append(escapeCsv(log.getTargetEntity())).append(",")
               .append(escapeCsv(log.getDetails())).append(",")
               .append(escapeCsv(log.getIpAddress())).append(",")
               .append(log.getSuccess() != null ? log.getSuccess() : "").append("\n");
        }

        // Audit the export action
        auditLogRepository.save(new AuditLog(
                getUsername(),
                getRole(),
                "AUDIT_LOG_EXPORT",
                "Exported " + logs.size() + " audit logs to CSV format.",
                null
        ));

        return ResponseEntity.ok()
                .header("Content-Disposition", "attachment; filename=audit_export.csv")
                .header("Content-Type", "text/csv; charset=UTF-8")
                .body(csv.toString());
    }

    private String getUsername() {
        return org.springframework.security.core.context.SecurityContextHolder.getContext().getAuthentication().getName();
    }

    private String getRole() {
        return org.springframework.security.core.context.SecurityContextHolder.getContext().getAuthentication().getAuthorities().stream()
                .map(a -> a.getAuthority().replace("ROLE_", ""))
                .findFirst().orElse("UNKNOWN");
    }

    private String escapeCsv(String value) {
        if (value == null) {
            return "";
        }
        String clean = value.replace("\"", "\"\"");
        if (clean.contains(",") || clean.contains("\n") || clean.contains("\"")) {
            return "\"" + clean + "\"";
        }
        return clean;
    }
}
