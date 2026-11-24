package com.mulenet.api.platform;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Base64;
import java.util.HexFormat;
import javax.crypto.Cipher;
import javax.crypto.Mac;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;

@Component
@Profile("platform")
public class PrivacyCodec {
    private final byte[] tokenKey;
    private final byte[] encryptionKey;
    private final SecureRandom random = new SecureRandom();

    public PrivacyCodec(@Value("${mulenet.token-key}") String tokenKey,
                        @Value("${mulenet.encryption-key}") String encryptionKey) {
        this.tokenKey = Base64.getDecoder().decode(tokenKey);
        this.encryptionKey = Base64.getDecoder().decode(encryptionKey);
        if (this.tokenKey.length < 32 || this.encryptionKey.length != 32) {
            throw new IllegalArgumentException("Independent token and AES-256 keys are required");
        }
    }

    public String token(String tenant, String domain, String value) {
        if (value == null) return null;
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(tokenKey, "HmacSHA256"));
            // Length-prefixed domains prevent delimiter collisions across tenants and identifiers.
            String input = tenant.length() + ":" + tenant + domain.length() + ":" + domain + value.length() + ":" + value;
            return HexFormat.of().formatHex(mac.doFinal(input.getBytes(StandardCharsets.UTF_8)));
        } catch (Exception e) { throw new IllegalStateException("Tokenization failed", e); }
    }

    public String encrypt(String tenant, String plaintext) {
        try {
            byte[] nonce = new byte[12];
            random.nextBytes(nonce);
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.ENCRYPT_MODE, new SecretKeySpec(encryptionKey, "AES"), new GCMParameterSpec(128, nonce));
            cipher.updateAAD(tenant.getBytes(StandardCharsets.UTF_8));
            byte[] ciphertext = cipher.doFinal(plaintext.getBytes(StandardCharsets.UTF_8));
            return "v1:" + Base64.getEncoder().encodeToString(nonce) + ":" + Base64.getEncoder().encodeToString(ciphertext);
        } catch (Exception e) { throw new IllegalStateException("Encryption failed", e); }
    }

    public String decrypt(String tenant, String encrypted) {
        try {
            String[] parts = encrypted.split(":", -1);
            if (parts.length != 3 || !parts[0].equals("v1")) throw new IllegalArgumentException("Unsupported ciphertext version");
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.DECRYPT_MODE, new SecretKeySpec(encryptionKey, "AES"), new GCMParameterSpec(128, Base64.getDecoder().decode(parts[1])));
            cipher.updateAAD(tenant.getBytes(StandardCharsets.UTF_8));
            return new String(cipher.doFinal(Base64.getDecoder().decode(parts[2])), StandardCharsets.UTF_8);
        } catch (Exception e) { throw new IllegalArgumentException("Ciphertext authentication failed", e); }
    }

    public static String hash(String value) {
        try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8))); }
        catch (Exception e) { throw new IllegalStateException(e); }
    }
}
