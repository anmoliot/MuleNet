package com.mulenet.api.model;

import jakarta.persistence.*;

@Entity
@Table(name = "policy_configurations")
public class PolicyConfig {
    @Id
    @Column(name = "config_key", unique = true, nullable = false, length = 128)
    private String configKey;

    @Column(name = "config_value", nullable = false)
    private Double configValue;

    public PolicyConfig() {}

    public PolicyConfig(String configKey, Double configValue) {
        this.configKey = configKey;
        this.configValue = configValue;
    }

    public String getConfigKey() { return configKey; }
    public void setConfigKey(String configKey) { this.configKey = configKey; }

    public Double getConfigValue() { return configValue; }
    public void setConfigValue(Double configValue) { this.configValue = configValue; }
}
