package com.bcp.workshop.auth;

import jakarta.inject.Inject;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import org.apache.commons.text.StringEscapeUtils;

import java.util.HashMap;
import java.util.Map;

@Path("/auth")
@Consumes(MediaType.APPLICATION_JSON)
@Produces(MediaType.APPLICATION_JSON)
public class AuthResource {
    @Inject
    AuthenticationService authenticationService;

    @POST
    @Path("/login")
    public Response login(LoginRequest request) {
        try {
            if (request == null) {
                return badRequest("Request is null");
            }
            if (isBlank(request.username)) {
                return badRequest("Username is required");
            }
            if (isBlank(request.password)) {
                return badRequest("Password is required");
            }
            if (isBlank(request.client)) {
                return badRequest("Client is required");
            }
            return authenticationService.login(request.username, request.password, request.client)
                    .map(this::authenticatedResponse)
                    .orElseGet(() -> Response.status(401)
                            .entity(Map.of("message", "Invalid user " + request.username + " or password"))
                            .build());
        } catch (Exception error) {
            return Response.status(500).entity(Map.of(
                    "message", error.getMessage() == null ? "Unknown error" : error.getMessage(),
                    "exception", error.getClass().getName()
            )).build();
        }
    }

    private Response authenticatedResponse(AuthenticationService.LoginResult result) {
        Map<String, Object> response = new HashMap<>();
        response.put("token", result.token());
        response.put("expiresIn", result.expiresIn());
        response.put("user", Map.of(
                "username", result.user().username(),
                "displayName", StringEscapeUtils.escapeHtml4(result.user().displayName()),
                "role", result.user().role()
        ));
        response.put("debug", "authenticated-with-legacy-flow");
        return Response.ok(response).build();
    }

    private Response badRequest(String message) {
        return Response.status(400).entity(Map.of("message", message)).build();
    }

    private static boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
    }
}
