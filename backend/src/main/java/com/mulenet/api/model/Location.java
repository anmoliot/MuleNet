package com.mulenet.api.model;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "locations")
public class Location {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "account_id", nullable = false, length = 64)
    private String accountId;

    @Column(nullable = false)
    private Double latitude;

    @Column(nullable = false)
    private Double longitude;

    @Column(length = 128)
    private String city;

    @Column(length = 64)
    private String country = "IN";

    @Column(name = "ip_address", length = 64)
    private String ipAddress;

    @Column(name = "is_tor")
    private Boolean isTor = false;

    @Column(name = "is_vpn")
    private Boolean isVpn = false;

    @Column(name = "geo_velocity_flag")
    private Boolean geoVelocityFlag = false;

    @Column(name = "recorded_at", nullable = false)
    private LocalDateTime recordedAt = LocalDateTime.now();

    public Location() {}

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public String getAccountId() { return accountId; }
    public void setAccountId(String accountId) { this.accountId = accountId; }

    public Double getLatitude() { return latitude; }
    public void setLatitude(Double latitude) { this.latitude = latitude; }

    public Double getLongitude() { return longitude; }
    public void setLongitude(Double longitude) { this.longitude = longitude; }

    public String getCity() { return city; }
    public void setCity(String city) { this.city = city; }

    public String getCountry() { return country; }
    public void setCountry(String country) { this.country = country; }

    public String getIpAddress() { return ipAddress; }
    public void setIpAddress(String ipAddress) { this.ipAddress = ipAddress; }

    public Boolean getIsTor() { return isTor; }
    public void setIsTor(Boolean tor) { isTor = tor; }

    public Boolean getIsVpn() { return isVpn; }
    public void setIsVpn(Boolean vpn) { isVpn = vpn; }

    public Boolean getGeoVelocityFlag() { return geoVelocityFlag; }
    public void setGeoVelocityFlag(Boolean geoVelocityFlag) { this.geoVelocityFlag = geoVelocityFlag; }

    public LocalDateTime getRecordedAt() { return recordedAt; }
    public void setRecordedAt(LocalDateTime recordedAt) { this.recordedAt = recordedAt; }
}
