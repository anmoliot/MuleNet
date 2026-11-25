package com.mulenet.api.platform;

import jakarta.servlet.*;
import jakarta.servlet.http.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.web.filter.OncePerRequestFilter;

final class RequestGuards extends OncePerRequestFilter {
    private static final int MAX_BYTES = 2_000_000;
    private final ConcurrentHashMap<String, Window> windows = new ConcurrentHashMap<>();
    private static final class Window {
        volatile long minute;
        int count;
        synchronized boolean allow(long now, int limit) {
            if (minute != now) { minute = now; count = 0; }
            return ++count <= limit;
        }
    }
    @Override protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain) throws ServletException, IOException {
        if (request.getParameter("token") != null || request.getParameter("access_token") != null) {
            response.sendError(401); return;
        }
        long minute = System.currentTimeMillis() / 60000;
        boolean login = request.getRequestURI().equals("/api/v1/auth/login");
        String key = request.getRemoteAddr() + (login ? ":login" : ":general");
        if (windows.size() >= 10000 && !windows.containsKey(key)) { response.sendError(429); return; }
        if (!windows.computeIfAbsent(key, ignored -> new Window()).allow(minute, login ? 5 : 600)) {
            response.setHeader("Retry-After", "60"); response.sendError(429); return;
        }
        if (windows.size() > 1000) windows.entrySet().removeIf(entry -> entry.getValue().minute < minute - 1);
        if (!"identity".equalsIgnoreCase(request.getHeader("Content-Encoding") == null ? "identity" : request.getHeader("Content-Encoding"))) {
            response.sendError(415); return;
        }
        if (!java.util.Set.of("POST", "PUT", "PATCH").contains(request.getMethod())) { chain.doFilter(request, response); return; }
        if (request.getContentLengthLong() > MAX_BYTES) { response.sendError(413); return; }
        byte[] body = request.getInputStream().readNBytes(MAX_BYTES + 1);
        if (body.length > MAX_BYTES) { response.sendError(413); return; }
        if (body.length > 0 && (request.getContentType() == null || !request.getContentType().split(";", 2)[0].equalsIgnoreCase("application/json"))) {
            response.sendError(415); return;
        }
        chain.doFilter(new HttpServletRequestWrapper(request) {
            @Override public ServletInputStream getInputStream() {
                ByteArrayInputStream input = new ByteArrayInputStream(body);
                return new ServletInputStream() {
                    @Override public int read() { return input.read(); }
                    @Override public int read(byte[] bytes, int offset, int length) { return input.read(bytes, offset, length); }
                    @Override public boolean isFinished() { return input.available() == 0; }
                    @Override public boolean isReady() { return true; }
                    @Override public void setReadListener(ReadListener listener) { throw new IllegalStateException("Request body is synchronously bounded before dispatch"); }
                };
            }
            @Override public BufferedReader getReader() { return new BufferedReader(new InputStreamReader(getInputStream(), StandardCharsets.UTF_8)); }
        }, response);
    }
}
