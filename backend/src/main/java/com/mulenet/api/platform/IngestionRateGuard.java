package com.mulenet.api.platform;

import jakarta.servlet.*;
import jakarta.servlet.http.*;
import java.io.IOException;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;

final class IngestionRateGuard extends OncePerRequestFilter {
    private final ConcurrentHashMap<String, long[]> counts = new ConcurrentHashMap<>();
    @Override protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain) throws ServletException, IOException {
        if (request.getRequestURI().equals("/api/v1/transactions") && request.getMethod().equals("POST")) {
            var auth = SecurityContextHolder.getContext().getAuthentication();
            if (auth != null && auth.isAuthenticated()) {
                String tenant = PlatformController.tenant(auth);
                long minute = System.currentTimeMillis() / 60000;
                String key = PrivacyCodec.hash(tenant + ":" + auth.getName());
                if (counts.size() >= 10000 && !counts.containsKey(key)) { response.sendError(429); return; }
                long[] state = counts.computeIfAbsent(key, ignored -> new long[]{minute, 0});
                synchronized (state) {
                    if (state[0] != minute) { state[0] = minute; state[1] = 0; }
                    if (++state[1] > 100) { response.setHeader("Retry-After", "60"); response.sendError(429); return; }
                }
                if (counts.size() > 1000) counts.entrySet().removeIf(entry -> { synchronized (entry.getValue()) { return entry.getValue()[0] < minute - 1; } });
            }
        }
        chain.doFilter(request, response);
    }
}
