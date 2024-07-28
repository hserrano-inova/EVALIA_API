from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from datetime import timedelta
from config import settings
from db import get_db
from models.users import Token, User, UserInDB
from auth import get_current_user, authenticate_user, get_password_hash, create_access_token

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Endpoints de autenticación y usuario
@router.post("/createuser", response_model=User, tags=["User"])
async def create_user(user: UserInDB):
    db = get_db()
    existing_user = db.users.find_one({"username": user.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = get_password_hash(user.hashed_password)
    user_dict = user.dict()
    user_dict["hashed_password"] = hashed_password
    db.users.insert_one(user_dict)
    return User(**user_dict)

@router.post("/token", response_model=Token, tags=["User"])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout", tags=["User"])
async def logout(current_user: User = Depends(get_current_user)):
    # En una implementación real, aquí se podría invalidar el token
    # Por ahora, simplemente retornamos un mensaje de éxito
    return {"message": "Successfully logged out"}
