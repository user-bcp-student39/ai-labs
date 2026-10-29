package com.bcp.workshop.auth;

import io.smallrye.jwt.algorithm.SignatureAlgorithm;
import io.smallrye.jwt.build.Jwt;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;

public class TokenIssuer {
    private static final Duration TOKEN_LIFETIME = Duration.ofHours(1);

    private final Clock clock;
    private final String signingKeyLocation;
    private final String issuer;
    private final String audience;

    public TokenIssuer(Clock clock, String signingKeyLocation, String issuer, String audience) {
        this.clock = clock;
        this.signingKeyLocation = signingKeyLocation;
        this.issuer = issuer;
        this.audience = audience;
    }

    public static long lifetimeSeconds() {
        return TOKEN_LIFETIME.toSeconds();
    }

    public String issue(String username, String role, String client) {
        requireConfigured();
        Instant issuedAt = clock.instant();
        return Jwt.claims()
                .issuer(issuer)
                .audience(audience)
                .subject(username)
                .claim("role", role)
                .claim("client", client)
                .issuedAt(issuedAt)
                .expiresAt(issuedAt.plus(TOKEN_LIFETIME))
                .jws()
                .algorithm(SignatureAlgorithm.RS256)
                .sign(signingKeyLocation);
    }

    private void requireConfigured() {
        if (isBlank(signingKeyLocation) || isBlank(issuer) || isBlank(audience)) {
            throw new IllegalStateException("Token signing is not configured");
        }
    }

    private static boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
    }
}
