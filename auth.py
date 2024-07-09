from fastapi import HTTPException, status, Depends
from passlib.context import CryptContext
from datetime import datetime, timedelta
from fastapi.security import  OAuth2PasswordBearer
import jwt
from config import settings
from models.users import UserInDB, TokenData
from db import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Función auxiliar para obtener el usuario actual
async def get_current_user(token: str = Depends(oauth2_scheme)):
    token_data = decode_token(token)
    db = get_db()
    user = db.users.find_one({"username": token_data.username})
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return UserInDB(**user)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def authenticate_user(username: str, password: str):
    db = get_db()
    user = db.users.find_one({"username": username})
    if not user:
        return False
    if not verify_password(password, user["hashed_password"]):
        return False
    return UserInDB(**user)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def decode_token(token: str):
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        token_data = TokenData(username=username)
        return token_data
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")