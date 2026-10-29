package com.bcp.workshop.auth;

import org.junit.jupiter.api.Test;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class TokenIssuerTest {
    private static final Instant ISSUED_AT = Instant.parse("2026-10-29T10:00:00Z");
    private static final Clock FIXED_CLOCK = Clock.fixed(ISSUED_AT, ZoneOffset.UTC);

    @Test
    void issuesRs256TokenWithRequiredClaims() {
        TokenIssuer issuer = new TokenIssuer(FIXED_CLOCK, JwtTestSupport.TEST_KEY_LOCATION, "workshop-auth-test", "workshop-api-test");

        String token = issuer.issue("student", "STUDENT", "angular-workshop");

        assertEquals("RS256", JwtTestSupport.header(token).get("alg"));
        assertTrue(JwtTestSupport.hasValidRs256Signature(token));
        Map<String, Object> claims = JwtTestSupport.claims(token);
        assertEquals("student", claims.get("sub"));
        assertEquals("angular-workshop", claims.get("client"));
        assertEquals("STUDENT", claims.get("role"));
        assertEquals("workshop-auth-test", claims.get("iss"));
        assertTrue(audienceContains(claims.get("aud"), "workshop-api-test"));
    }

    @Test
    void tokenExpiresOneHourAfterIssuance() {
        TokenIssuer issuer = new TokenIssuer(FIXED_CLOCK, JwtTestSupport.TEST_KEY_LOCATION, "workshop-auth-test", "workshop-api-test");

        Map<String, Object> claims = JwtTestSupport.claims(issuer.issue("student", "STUDENT", "angular-workshop"));

        long issuedAt = ((Number) claims.get("iat")).longValue();
        long expiresAt = ((Number) claims.get("exp")).longValue();
        assertEquals(ISSUED_AT.getEpochSecond(), issuedAt);
        assertTrue(expiresAt > issuedAt);
        assertEquals(3600L, expiresAt - issuedAt);
        assertEquals(3600L, TokenIssuer.lifetimeSeconds());
    }

    @Test
    void refusesToIssueWithoutSigningKey() {
        TokenIssuer issuer = new TokenIssuer(FIXED_CLOCK, "", "workshop-auth-test", "workshop-api-test");

        IllegalStateException error = assertThrows(IllegalStateException.class,
                () -> issuer.issue("student", "STUDENT", "angular-workshop"));
        assertEquals("Token signing is not configured", error.getMessage());
    }

    @Test
    void refusesToIssueWithoutIssuer() {
        TokenIssuer issuer = new TokenIssuer(FIXED_CLOCK, JwtTestSupport.TEST_KEY_LOCATION, " ", "workshop-api-test");

        assertThrows(IllegalStateException.class,
                () -> issuer.issue("student", "STUDENT", "angular-workshop"));
    }

    private static boolean audienceContains(Object audience, String expected) {
        if (audience instanceof List<?> values) {
            return values.contains(expected);
        }
        return expected.equals(audience);
    }
}
