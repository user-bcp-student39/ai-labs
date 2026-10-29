package com.bcp.workshop.auth;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.security.KeyFactory;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.security.Signature;
import java.security.interfaces.RSAPrivateCrtKey;
import java.security.interfaces.RSAPublicKey;
import java.security.spec.PKCS8EncodedKeySpec;
import java.security.spec.RSAPublicKeySpec;
import java.util.Base64;
import java.util.Map;

final class JwtTestSupport {
    static final String TEST_KEY_LOCATION = "jwt/test-private-key.pem";

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private JwtTestSupport() {
    }

    static Map<String, Object> header(String token) {
        return decodeSegment(token, 0);
    }

    static Map<String, Object> claims(String token) {
        return decodeSegment(token, 1);
    }

    static boolean hasValidRs256Signature(String token) {
        String[] parts = token.split("\\.");
        try {
            Signature verifier = Signature.getInstance("SHA256withRSA");
            verifier.initVerify(testPublicKey());
            verifier.update((parts[0] + "." + parts[1]).getBytes(StandardCharsets.US_ASCII));
            return verifier.verify(Base64.getUrlDecoder().decode(parts[2]));
        } catch (Exception error) {
            throw new IllegalStateException("Signature check failed", error);
        }
    }

    private static Map<String, Object> decodeSegment(String token, int index) {
        byte[] json = Base64.getUrlDecoder().decode(token.split("\\.")[index]);
        try {
            return MAPPER.readValue(json, new TypeReference<Map<String, Object>>() {
            });
        } catch (IOException error) {
            throw new UncheckedIOException(error);
        }
    }

    private static RSAPublicKey testPublicKey() throws Exception {
        PrivateKey privateKey = readTestPrivateKey();
        RSAPrivateCrtKey crtKey = (RSAPrivateCrtKey) privateKey;
        PublicKey publicKey = KeyFactory.getInstance("RSA")
                .generatePublic(new RSAPublicKeySpec(crtKey.getModulus(), crtKey.getPublicExponent()));
        return (RSAPublicKey) publicKey;
    }

    private static PrivateKey readTestPrivateKey() throws Exception {
        String pem;
        try (InputStream stream = JwtTestSupport.class.getClassLoader().getResourceAsStream(TEST_KEY_LOCATION)) {
            pem = new String(stream.readAllBytes(), StandardCharsets.US_ASCII);
        }
        String body = pem.replaceAll("-----[A-Z ]+-----", "").replaceAll("\\s", "");
        byte[] der = Base64.getDecoder().decode(body);
        return KeyFactory.getInstance("RSA").generatePrivate(new PKCS8EncodedKeySpec(der));
    }
}
