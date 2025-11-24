import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from pymongo import MongoClient, ASCENDING
import bcrypt
from jose import jwt, JWTError
from dotenv import load_dotenv
from bson import ObjectId
from fastapi.middleware.cors import CORSMiddleware


load_dotenv()


MONGO_URI = os.getenv("MONGO_URI")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXP_DELTA_SECONDS = int(os.getenv("JWT_EXP_DELTA_SECONDS", "3600"))

client = MongoClient(MONGO_URI)
db = client["user_agent_db"]
users_collection = db["users"]
memory_collection = db["user_memory"]

# Ensure index on email
users_collection.create_index([("email", ASCENDING)], unique=True)
memory_collection.create_index([("user_id", ASCENDING)], unique=True)

app = FastAPI(title="Auth for SMA")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173/"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Pydantic models
class SignupModel(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

def hash_password(plain_password: str) -> bytes:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())

def verify_password(plain_password: str, hashed: bytes) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed)

def create_token(user_id: str) -> str:
    exp = datetime.utcnow() + timedelta(seconds=JWT_EXP_DELTA_SECONDS)
    payload = {"sub": str(user_id), "exp": exp}
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide")

def get_user_by_email(email: str):
    return users_collection.find_one({"email": email})

def get_user_by_id(user_id: str):
    return users_collection.find_one({"_id": ObjectId(user_id)})

@app.post("/signup", status_code=201)
def signup(payload: SignupModel):
    if get_user_by_email(payload.email):
        raise HTTPException(status_code=400, detail="Email déjà utilisé.")

    hashed = hash_password(payload.password)
    user_doc = {
        "email": payload.email,
        "password_hash": hashed,
        "name": payload.name,
        "created_at": datetime.utcnow()
    }
    res = users_collection.insert_one(user_doc)
    user_id = res.inserted_id

    # create empty memory doc
    memory_doc = {
        "user_id": user_id,
        "likes": [],
        "dislikes": [],
        "personal_info": {},
        "updated_at": datetime.utcnow()
    }
    memory_collection.insert_one(memory_doc)

    return {"msg": "Compte créé", "user_id": str(user_id)}

@app.post("/token", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user_by_email(form_data.username)
    if not user:
        raise HTTPException(status_code=400, detail="Utilisateur non trouvé.")

    if not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Mot de passe invalide.")

    token = create_token(str(user["_id"]))
    return {"access_token": token, "token_type": "bearer", "expires_in": JWT_EXP_DELTA_SECONDS}

# Dependency to get current user object from token
def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token invalide")
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")
    # convert _id for convenience
    user["id"] = str(user["_id"])
    return user

# Example protected route
@app.get("/me")
def read_my_profile(current_user: dict = Depends(get_current_user)):
    mem = memory_collection.find_one({"user_id": ObjectId(current_user["id"])})
    return {
        "email": current_user["email"],
        "name": current_user.get("name"),
        "memory": {
            "likes": mem.get("likes", []),
            "dislikes": mem.get("dislikes", [])
        }
    }
