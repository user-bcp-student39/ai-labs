from fastapi import HTTPException


def authorize_owner(requested_owner: str, identity_username: str) -> str:
    if requested_owner != identity_username:
        raise HTTPException(status_code=403, detail="Not authorized for requested owner")
    return identity_username
