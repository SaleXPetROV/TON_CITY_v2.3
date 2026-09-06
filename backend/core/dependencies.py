"""
FastAPI dependencies for authentication
"""
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from typing import Optional

from .database import db
from .config import SECRET_KEY, ALGORITHM, ADMIN_WALLET
from .models import User

from auth_cookie import CookieOrBearer
security = CookieOrBearer(auto_error=False)


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Get current authenticated user from JWT token"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        identifier: str = payload.get("sub")
        if not identifier:
            raise HTTPException(status_code=401, detail="Invalid token")
        token_sid = payload.get("sid")
        
        # Find user by wallet_address, email, or username
        user_doc = await db.users.find_one({
            "$or": [
                {"wallet_address": identifier},
                {"email": identifier},
                {"username": identifier}
            ]
        })
        
        if not user_doc:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        # NOTE: single-session enforcement intentionally DISABLED.
        # Per product decision, a token issued at login must keep working until
        # the user explicitly logs out — we do NOT invalidate a session just
        # because another login rotated `session_id`. (This removes the
        # self-kick / multi-device ping-pong where a freshly-issued token was
        # dropped and the user landed on the guest screen despite "login ok".)
        current_sid = user_doc.get("session_id")
        if token_sid and not current_sid:
            await db.users.update_one({"_id": user_doc["_id"]}, {"$set": {"session_id": token_sid}})
        
        # Normalize is_admin field to boolean
        if "is_admin" in user_doc:
            if isinstance(user_doc["is_admin"], str):
                user_doc["is_admin"] = user_doc["is_admin"].lower() in ("true", "1", "yes")
            elif not isinstance(user_doc["is_admin"], bool):
                user_doc["is_admin"] = False
        else:
            user_doc["is_admin"] = False
        
        # Auto-grant admin if wallet matches ADMIN_WALLET from env
        wallet_addr = user_doc.get("wallet_address", "") or user_doc.get("wallet_address_raw", "")
        if ADMIN_WALLET and wallet_addr and (wallet_addr == ADMIN_WALLET or wallet_addr.lower() == ADMIN_WALLET.lower()):
            user_doc["is_admin"] = True
        
        return User(**user_doc)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_admin(current_user: User = Depends(get_current_user)):
    """Verify user has admin privileges (S5: generic 'Forbidden').

    Matches server.py::get_current_admin strict semantics: require is_admin=True
    OR wallet_address matches a non-empty ADMIN_WALLET. This prevents a bypass
    when both ADMIN_WALLET and user.wallet_address are None/empty (None != None
    is False, which previously allowed access to all admin routes)."""
    if current_user.is_admin:
        return current_user
    if ADMIN_WALLET and current_user.wallet_address and current_user.wallet_address == ADMIN_WALLET:
        return current_user
    raise HTTPException(status_code=403, detail="Forbidden")


# Alias for compatibility
get_admin_user = get_current_admin


# S8: Admin dependency with 2FA gate for dangerous operations.
async def get_current_admin_with_2fa(
    request: Request,
    admin: User = Depends(get_current_admin),
):
    admin_doc = await db.users.find_one({"id": admin.id}, {"_id": 0})
    if not admin_doc and admin.email:
        admin_doc = await db.users.find_one({"email": admin.email}, {"_id": 0})
    if admin_doc and admin_doc.get("is_2fa_enabled") and admin_doc.get("two_factor_secret"):
        code = request.headers.get("X-Admin-TOTP") or request.headers.get("x-admin-totp")
        if not code:
            raise HTTPException(status_code=401, detail="TOTP required for this admin action")
        try:
            import pyotp
            from security.totp_crypto import decrypt_secret
            totp = pyotp.TOTP(decrypt_secret(admin_doc["two_factor_secret"]))
            if not totp.verify(str(code), valid_window=1):
                raise HTTPException(status_code=401, detail="Invalid TOTP code")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid TOTP code")
    return admin
