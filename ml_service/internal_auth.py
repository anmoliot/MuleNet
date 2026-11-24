"""Short-lived, scoped service JWTs; no end-user JWT is accepted here."""

import time

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt

bearer = HTTPBearer(auto_error=False)


def service_authorizer(secret):
    if len(secret.encode()) < 48:
        raise RuntimeError("MULENET_SERVICE_SECRET must contain at least 48 random characters")

    def principal(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
        if not credentials:
            raise HTTPException(401, "Service authentication required")
        try:
            claims = jwt.decode(credentials.credentials, secret, algorithms=["HS256"],
                                audience="mulenet-ml", issuer="mulenet-backend", leeway=3,
                                options={"require": ["exp", "iat", "iss", "aud", "sub", "tenant", "scope", "jti"]})
            if claims["sub"] != "backend" or not isinstance(claims["iat"], int) or not isinstance(claims["exp"], int):
                raise ValueError("Invalid service subject or clock")
            if claims["exp"] - claims["iat"] > 60 or claims["iat"] > time.time() + 3:
                raise ValueError("Service token lifetime exceeds limit")
            if not isinstance(claims["tenant"], str) or not 1 <= len(claims["tenant"]) <= 128:
                raise ValueError("Invalid tenant")
            if not isinstance(claims["scope"], str) or not isinstance(claims["jti"], str):
                raise ValueError("Invalid scope or token ID")
            return claims
        except (jwt.InvalidTokenError, ValueError, TypeError):
            raise HTTPException(401, "Invalid service credential") from None

    def require(scope):
        def authorized(claims=Depends(principal)):
            if scope not in claims["scope"].split():
                raise HTTPException(403, "Insufficient service scope")
            return claims
        return authorized

    return require
