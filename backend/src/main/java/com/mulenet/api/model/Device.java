package com.mulenet.api.model;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "devices")
public class Device {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "device_id", nullable = false, unique = true, length = 128)
    private String deviceId;

    @Column(name = "device_type", length = 32)
    private String deviceType = "MOBILE";

    @Column(name = "os_type", length = 32)
    private String osType;

    @Column(name = "fingerprint_hash", length = 256)
    private String fingerprintHash;

    @Column(name = "is_blacklisted")
    private Boolean isBlacklisted = false;

    @Column(name = "sim_swap_flag")
    private Boolean simSwapFlag = false;

    @Column(name = "shared_account_count")
    private Integer sharedAccountCount = 0;

    @Column(name = "first_seen", nullable = false)
    private LocalDateTime firstSeen = LocalDateTime.now();

    @Column(name = "last_seen", nullable = false)
    private LocalDateTime lastSeen = LocalDateTime.now();

    public Device() {}

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public String getDeviceId() { return deviceId; }
    public void setDeviceId(String deviceId) { this.deviceId = deviceId; }

    public String getDeviceType() { return deviceType; }
    public void setDeviceType(String deviceType) { this.deviceType = deviceType; }

    public String getOsType() { return osType; }
    public void setOsType(String osType) { this.osType = osType; }

    public String getFingerprintHash() { return fingerprintHash; }
    public void setFingerprintHash(String fingerprintHash) { this.fingerprintHash = fingerprintHash; }

    public Boolean getIsBlacklisted() { return isBlacklisted; }
    public void setIsBlacklisted(Boolean blacklisted) { isBlacklisted = blacklisted; }

    public Boolean getSimSwapFlag() { return simSwapFlag; }
    public void setSimSwapFlag(Boolean simSwapFlag) { this.simSwapFlag = simSwapFlag; }

    public Integer getSharedAccountCount() { return sharedAccountCount; }
    public void setSharedAccountCount(Integer sharedAccountCount) { this.sharedAccountCount = sharedAccountCount; }

    public LocalDateTime getFirstSeen() { return firstSeen; }
    public void setFirstSeen(LocalDateTime firstSeen) { this.firstSeen = firstSeen; }

    public LocalDateTime getLastSeen() { return lastSeen; }
    public void setLastSeen(LocalDateTime lastSeen) { this.lastSeen = lastSeen; }
}
