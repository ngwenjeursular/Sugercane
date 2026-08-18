from datetime import datetime,timezone
from fastapi import Cookie,Depends,Header,HTTPException
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.security import token_hash,safe_equal
from app.db.session import get_db
from app.models import Session as UserSession,User
settings=get_settings()
def current_session(db:Session=Depends(get_db),session_cookie:str|None=Cookie(default=None,alias=settings.session_cookie_name)):
    if not session_cookie: raise HTTPException(401,"Authentication required")
    s=db.query(UserSession).filter(UserSession.token_hash==token_hash(session_cookie)).first()
    if not s or s.expires_at<=datetime.now(timezone.utc): raise HTTPException(401,"Authentication required")
    return s
def current_user(s=Depends(current_session),db:Session=Depends(get_db)):
    u=db.query(User).filter(User.id==s.user_id).first()
    if not u or not u.is_active: raise HTTPException(401,"Account unavailable")
    return u
def csrf(s=Depends(current_session),token:str|None=Header(default=None,alias="X-CSRF-Token")):
    if not token or not safe_equal(token_hash(token),s.csrf_hash): raise HTTPException(403,"CSRF validation failed")
