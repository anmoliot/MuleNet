package com.mulenet.api.platform;

import org.springframework.core.env.Environment;
import org.springframework.stereotype.Component;

@Component
public class ConfigurationGuard {
    public ConfigurationGuard(Environment environment) {
        boolean migrate = environment.matchesProfiles("migrate");
        boolean platform = environment.matchesProfiles("platform");
        if ((!migrate && !platform) || (migrate && platform))
            throw new IllegalArgumentException("Select platform, platform plus demo, or an isolated migrate profile; legacy authentication is retired");
    }
}
