#from fastapi import APIRouter,Depends,HTTPException,Response
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.api.deps import current_user
from app.core.config import get_settings
from app.core.security import expires_at,hash_password,new_token,token_hash,verify_password
from app.db.session import get_db
from app.models import Session as UserSession,User,Wallet
from app.schemas.auth import LoginRequest,RegisterRequest,UserResponse
router=APIRouter(prefix="/auth")
settings=get_settings()
def cookies(r,t,c):
    r.set_cookie(settings.session_cookie_name,t,httponly=True,secure=settings.cookie_secure,samesite="lax",max_age=settings.session_ttl_hours*3600)
    r.set_cookie(settings.csrf_cookie_name,c,httponly=False,secure=settings.cookie_secure,samesite="lax",max_age=settings.session_ttl_hours*3600)
@router.post("/register",response_model=UserResponse,status_code=201)
def register(p:RegisterRequest,r:Response,db:Session=Depends(get_db)):
    if db.query(User).filter(User.phone_number==p.phone_number).first(): raise HTTPException(409,"Account already exists")
    parent=db.query(User).filter(User.referral_code==p.referral_code).first() if p.referral_code else None
    if p.referral_code and not parent: raise HTTPException(400,"Invalid referral code")
    u=User(full_name=p.full_name.strip(),phone_number=p.phone_number,password_hash=hash_password(p.password),referral_code=f"SC-{new_token()[:8].upper()}",referred_by_id=parent.id if parent else None)
    db.add(u)
    try:
        db.flush(); db.add(Wallet(user_id=u.id)); st,ct=new_token(),new_token(); db.add(UserSession(user_id=u.id,token_hash=token_hash(st),csrf_hash=token_hash(ct),expires_at=expires_at())); db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(409,"Could not create account")
    cookies(r,st,ct); return UserResponse(id=str(u.id),full_name=u.full_name,phone_number=u.phone_number,referral_code=u.referral_code)
@router.post("/login",response_model=UserResponse)
def login(p:LoginRequest,r:Response,db:Session=Depends(get_db)):
    u=db.query(User).filter(User.phone_number==p.phone_number).first()
    if not u or not verify_password(p.password,u.password_hash): raise HTTPException(401,"Invalid credentials")
    if not u.is_active: raise HTTPException(403,"Account unavailable")
    st,ct=new_token(),new_token(); db.add(UserSession(user_id=u.id,token_hash=token_hash(st),csrf_hash=token_hash(ct),expires_at=expires_at())); db.commit(); cookies(r,st,ct)
    return UserResponse(id=str(u.id),full_name=u.full_name,phone_number=u.phone_number,referral_code=u.referral_code)

@router.post("/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    u=Depends(current_user),
    db: Session = Depends(get_db),
):
    session_token = request.cookies.get(
        settings.session_cookie_name
    )

    if session_token:
        db.query(UserSession).filter(
            UserSession.token_hash == token_hash(session_token)
        ).delete()

        db.commit()

    response.delete_cookie(
        settings.session_cookie_name
    )

    response.delete_cookie(
        settings.csrf_cookie_name
    )
    
@router.get("/me", response_model=UserResponse)
def me(u=Depends(current_user)):
    return UserResponse(
        id=str(u.id),
        full_name=u.full_name,
        phone_number=u.phone_number,
        referral_code=u.referral_code,
    )