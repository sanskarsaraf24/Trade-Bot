from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from config import get_settings
from database.session import get_db, SessionLocal
from database.models import User, TradingConfiguration

settings = get_settings()
router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ─── Pydantic schemas ────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str


# ─── Helpers ───────────────────────────────────────────────
default_rounds = 12

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(default_rounds)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=settings.jwt_expire_hours))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        user_id: str = payload.get("sub")
        if not user_id:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise credentials_exception
    return user


# ─── Endpoints ────────────────────────────────────────────────
@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Registration is disabled. Use the predefined system password to login."""
    raise HTTPException(status_code=403, detail="Registration disabled. Use standard login.")


@router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # The only valid password for this system
    REQUIRED_PASSWORD = "admin123"
    
    if form_data.password != REQUIRED_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # We use a single 'admin' user for everything. Create it if it doesn't exist.
    admin_email = "admin@trade.system"
    user = db.query(User).filter(User.email == admin_email).first()
    
    if not user:
        user = User(
            email=admin_email,
            hashed_password=hash_password(REQUIRED_PASSWORD),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token({"sub": user.id})
    return TokenResponse(access_token=token, user_id=user.id, email=user.email)


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return {"user_id": current_user.id, "email": current_user.email}


@router.get("/kite/login")
async def kite_login(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns the Zerodha login URL for the user to authenticate.
    """
    config = db.query(TradingConfiguration).filter(
        TradingConfiguration.user_id == current_user.id
    ).first()
    api_key = (config.broker_api_key if config else "") or settings.zerodha_api_key
    if not api_key:
        raise HTTPException(status_code=400, detail="Zerodha API Key missing in config")

    # We don't need secret or token yet just to generate the URL
    login_url = f"https://kite.zerodha.com/connect/login?v=3&api_key={api_key}"
    return {"login_url": login_url}


@router.get("/kite/callback")
async def kite_callback(
    request_token: str = Query(...),
    status: str = Query(None),
    db: Session = Depends(get_db)
):
    """
    Zerodha Kite redirect callback.
    Exchange request_token for access_token and save to config.
    """
    # We assume the first user for simplicity in this single-tenant deployment
    config = db.query(TradingConfiguration).first()
    api_key = (config.broker_api_key if config else "") or settings.zerodha_api_key
    api_secret = (config.broker_api_secret if config else "") or settings.zerodha_api_secret
    if not config or not api_key or not api_secret:
        # Redirect with error
        return RedirectResponse(url="/config?auth=error&reason=config_missing")

    try:
        from services.broker_connector import ZerodhaBroker
        broker = ZerodhaBroker(
            api_key=api_key,
            api_secret=api_secret,
            request_token=request_token
        )
        
        # Save the generated access token
        config.broker_access_token = broker.access_token
        config.updated_at = datetime.utcnow()
        db.commit()
        
        # Redirect back to config page with success param
        return RedirectResponse(url="/config?auth=success")
    except Exception as e:
        return RedirectResponse(url=f"/config?auth=error&reason={str(e)}")


@router.post("/kite/postback")
async def kite_postback(data: dict):
    """
    Zerodha order postback webhook.
    """
    # Logging for now
    from database.session import SessionLocal
    from database.models import SystemLog
    db = SessionLocal()
    try:
        log = SystemLog(
            user_id="SYSTEM", # Placeholder or find via order_id
            event_type="kite_postback",
            message=f"Kite postback received: {data.get('status')}",
            severity="info"
        )
        db.add(log)
        db.commit()
    finally:
        db.close()
    return {"status": "received"}
