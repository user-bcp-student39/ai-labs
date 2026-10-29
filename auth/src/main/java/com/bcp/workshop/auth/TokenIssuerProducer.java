package com.bcp.workshop.auth;

import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.inject.Produces;
import jakarta.inject.Singleton;
import org.eclipse.microprofile.config.inject.ConfigProperty;

import java.time.Clock;

@ApplicationScoped
public class TokenIssuerProducer {
    @Produces
    @Singleton
    Clock clock() {
        return Clock.systemUTC();
    }

    @Produces
    @Singleton
    TokenIssuer tokenIssuer(
            Clock clock,
            @ConfigProperty(name = "auth.token.signing-key") String signingKey,
            @ConfigProperty(name = "auth.token.issuer") String issuer,
            @ConfigProperty(name = "auth.token.audience") String audience) {
        return new TokenIssuer(clock, signingKey, issuer, audience);
    }
}
