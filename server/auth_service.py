import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from pydantic_settings import BaseSettings
from pymongo import MongoClient, ASCENDING
import bcrypt
from jose import jwt, JWTError
from bson import ObjectId

# Note: On n'importe plus google.generativeai ici car l'UserAgent gère Groq en interne.

# --- IMPORT DU NOUVEL AGENT ---
from agents.user_agent import UserAgent

# --- 1. CONFIGURATION ---
class Settings(BaseSettings):
    MONGO_URI: str
    JWT_SECRET: str
    # On remplace Gemini par Groq dans la validation
    GROQ_API_KEY: str 
    SERPAPI_KEY: Optional[str] = None
    
    JWT_ALGORITHM: str = "HS256"
    JWT_EXP_DELTA_SECONDS: int = 3600
    
    class Config:
        env_file = ".env"
        extra = "ignore" 

settings = Settings()

# --- 2. BASE DE DONNÉES ---
client = MongoClient(settings.MONGO_URI)
db = client["user_agent_db"]
users_collection = db["users"]
memory_collection = db["user_memory"]

# Index pour la rapidité et l'unicité
users_collection.create_index([("email", ASCENDING)], unique=True)
memory_collection.create_index([("user_id", ASCENDING)], unique=True)

# --- 3. INITIALISATION AGENT ---
# L'agent s'initialise et se connecte à Groq tout seul (voir agents/user_agent.py)
agent = UserAgent(db)

# --- 4. FASTAPI SETUP ---
app = FastAPI(title="SMA Unified API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- 5. MODÈLES & UTILITAIRES ---
class SignupModel(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class ChatRequest(BaseModel):
    message: str

def hash_password(plain_password: str) -> bytes:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())

def verify_password(plain_password: str, hashed: bytes) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed)

def create_token(user_id: str) -> str:
    exp = datetime.utcnow() + timedelta(seconds=settings.JWT_EXP_DELTA_SECONDS)
    payload = {"sub": str(user_id), "exp": exp}
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token invalide")
        user = users_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=401, detail="Utilisateur introuvable")
        user["id"] = str(user["_id"])
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide")

# --- 6. ROUTES ---

@app.post("/signup", status_code=201)
def signup(payload: SignupModel):
    if users_collection.find_one({"email": payload.email}):
        raise HTTPException(status_code=400, detail="Email déjà utilisé.")

    hashed = hash_password(payload.password)
    user_doc = {
        "email": payload.email,
        "password_hash": hashed,
        "name": payload.name,
        "created_at": datetime.utcnow()
    }
    res = users_collection.insert_one(user_doc)
    
    # Init mémoire vide
    memory_collection.insert_one({
        "user_id": res.inserted_id,
        "likes": [],
        "dislikes": [],
        "updated_at": datetime.utcnow()
    })

    return {"msg": "Compte créé", "user_id": str(res.inserted_id)}

@app.post("/token", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = users_collection.find_one({"email": form_data.username})
    if not user or not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Identifiants invalides.")

    token = create_token(str(user["_id"]))
    return {"access_token": token, "expires_in": settings.JWT_EXP_DELTA_SECONDS}

@app.get("/me")
def read_my_profile(current_user: dict = Depends(get_current_user)):
    mem = memory_collection.find_one({"user_id": ObjectId(current_user["id"])})
    return {
        "email": current_user["email"],
        "name": current_user.get("name"),
        "memory": {
            "likes": mem.get("likes", []) if mem else [],
            "dislikes": mem.get("dislikes", []) if mem else []
        }
    }

@app.post("/chat")
def chat(payload: ChatRequest, current_user: dict = Depends(get_current_user)):
    """
    Route Chat : Délègue tout à l'UserAgent (qui utilise maintenant Groq).
    """
    response = agent.process_message(current_user["id"], payload.message)
    return {"response": response}