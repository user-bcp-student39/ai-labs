package com.bcp.workshop.auth;

import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;

import java.util.Optional;

@ApplicationScoped
public class AuthenticationService {
    @Inject
    LegacyDatabase database;

    @Inject
    TokenIssuer tokenIssuer;

    public Optional<LoginResult> login(String username, String password, String client) {
        UserRecord user = database.findByCredentials(username, password);
        if (user == null) {
            return Optional.empty();
        }
        String token = tokenIssuer.issue(user.username(), user.role(), client.trim());
        return Optional.of(new LoginResult(token, TokenIssuer.lifetimeSeconds(), user));
    }

    public record LoginResult(String token, long expiresIn, UserRecord user) {
    }
}
