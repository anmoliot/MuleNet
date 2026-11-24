package com.mulenet.api.platform;

import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;

@Component
@Profile("migrate")
public class MigrationExit implements CommandLineRunner {
    private final ConfigurableApplicationContext context;
    public MigrationExit(ConfigurableApplicationContext context) { this.context = context; }
    public void run(String... args) { System.exit(SpringApplication.exit(context)); }
}
