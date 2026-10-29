package com.bcp.workshop.auth;

import io.quarkus.test.junit.QuarkusTest;
import io.restassured.response.Response;
import org.junit.jupiter.api.Test;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Map;

import static io.restassured.RestAssured.given;
import static org.hamcrest.CoreMatchers.is;
import static org.hamcrest.Matchers.notNullValue;
import static org.hamcrest.Matchers.nullValue;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

@QuarkusTest
class AuthResourceTest {
    private static final String VALID_LOGIN_BODY =
            "{\"username\":\"student\",\"password\":\"Workshop123!\",\"client\":\"angular-workshop\"}";

    @Test
    void logsInWithWorkshopUser() {
        given()
                .contentType("application/json")
                .body(VALID_LOGIN_BODY)
                .when().post("/auth/login")
                .then()
                .statusCode(200)
                .body("user.username", is("student"))
                .body("token", notNullValue());
    }

    // Protege el contrato de respuesta exitosa: token, expiresIn y campos de user.
    @Test
    void successfulLoginKeepsResponseContract() {
        given()
                .contentType("application/json")
                .body(VALID_LOGIN_BODY)
                .when().post("/auth/login")
                .then()
                .statusCode(200)
                .body("token", notNullValue())
                .body("expiresIn", is(3600))
                .body("user.username", is("student"))
                .body("user.displayName", is("Workshop Student"))
                .body("user.role", is("STUDENT"));
    }

    // Protege el 401 de credenciales inválidas y la ausencia de token en esa respuesta.
    @Test
    void invalidCredentialsReturnUnauthorizedWithoutToken() {
        given()
                .contentType("application/json")
                .body("{\"username\":\"student\",\"password\":\"wrong-password\",\"client\":\"angular-workshop\"}")
                .when().post("/auth/login")
                .then()
                .statusCode(401)
                .body("token", nullValue());
    }

    // Protege la validación actual de username ausente como 400.
    @Test
    void missingUsernameReturnsBadRequest() {
        given()
                .contentType("application/json")
                .body("{\"password\":\"Workshop123!\",\"client\":\"angular-workshop\"}")
                .when().post("/auth/login")
                .then()
                .statusCode(400)
                .body("token", nullValue());
    }

    // Protege la validación actual de password ausente como 400.
    @Test
    void missingPasswordReturnsBadRequest() {
        given()
                .contentType("application/json")
                .body("{\"username\":\"student\",\"client\":\"angular-workshop\"}")
                .when().post("/auth/login")
                .then()
                .statusCode(400)
                .body("token", nullValue());
    }

    // Protege la validación de client ausente: sin client no se emite token.
    @Test
    void missingClientReturnsBadRequestWithoutToken() {
        given()
                .contentType("application/json")
                .body("{\"username\":\"student\",\"password\":\"Workshop123!\"}")
                .when().post("/auth/login")
                .then()
                .statusCode(400)
                .body("token", nullValue());
    }

    // Protege la validación de client en blanco: solo espacios se rechazan sin token.
    @Test
    void blankClientReturnsBadRequestWithoutToken() {
        given()
                .contentType("application/json")
                .body("{\"username\":\"student\",\"password\":\"Workshop123!\",\"client\":\"   \"}")
                .when().post("/auth/login")
                .then()
                .statusCode(400)
                .body("token", nullValue());
    }

    // Protege que el claim client es el valor recortado de la solicitud.
    @Test
    void clientClaimIsTrimmedAndBoundToToken() {
        String token = given()
                .contentType("application/json")
                .body("{\"username\":\"student\",\"password\":\"Workshop123!\",\"client\":\"  angular-workshop  \"}")
                .when().post("/auth/login")
                .then()
                .statusCode(200)
                .extract().path("token");

        Map<String, Object> claims = JwtTestSupport.claims(token);
        assertEquals("angular-workshop", claims.get("client"));
        assertEquals("student", claims.get("sub"));
        assertEquals("STUDENT", claims.get("role"));
    }

    // Protege la coherencia entre expiresIn y exp, con tolerancia de un segundo.
    @Test
    void expiresInMatchesTokenExpiryWithinOneSecond() {
        Response response = given()
                .contentType("application/json")
                .body(VALID_LOGIN_BODY)
                .when().post("/auth/login")
                .then()
                .statusCode(200)
                .extract().response();

        long expiresIn = ((Number) response.path("expiresIn")).longValue();
        long expiresAt = ((Number) JwtTestSupport.claims(response.path("token")).get("exp")).longValue();
        long now = Instant.now().getEpochSecond();
        assertTrue(Math.abs(expiresIn - (expiresAt - now)) <= 1);
    }

    // Protege que login no registra el token ni material de clave en la salida.
    @Test
    void loginOutputDoesNotExposeTokenOrKeyMaterial() {
        PrintStream originalOut = System.out;
        PrintStream originalErr = System.err;
        ByteArrayOutputStream captured = new ByteArrayOutputStream();
        PrintStream capture = new PrintStream(captured, true, StandardCharsets.UTF_8);
        String token;
        System.setOut(capture);
        System.setErr(capture);
        try {
            token = given()
                    .contentType("application/json")
                    .body(VALID_LOGIN_BODY)
                    .when().post("/auth/login")
                    .then()
                    .statusCode(200)
                    .extract().path("token");
            given()
                    .contentType("application/json")
                    .body("{\"username\":\"student\",\"password\":\"wrong-password\",\"client\":\"angular-workshop\"}")
                    .when().post("/auth/login")
                    .then()
                    .statusCode(401);
        } finally {
            System.setOut(originalOut);
            System.setErr(originalErr);
        }
        String output = captured.toString(StandardCharsets.UTF_8);
        assertFalse(output.contains(token));
        assertFalse(output.contains("PRIVATE KEY"));
    }
}
