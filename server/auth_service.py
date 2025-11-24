import os
import json
import re
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from pydantic_settings import BaseSettings
from pymongo import MongoClient, ASCENDING
import bcrypt
from jose import jwt, JWTError
from bson import ObjectId
import google.generativeai as genai

# --- 1. CONFIGURATION ---
class Settings(BaseSettings):
    MONGO_URI: str
    JWT_SECRET: str
    GEMINI_API_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXP_DELTA_SECONDS: int = 3600
    
    class Config:
        env_file = ".env"
        extra = "ignore" 

settings = Settings()

# Configuration Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)

# --- 2. BASE DE DONNÉES ---
client = MongoClient(settings.MONGO_URI)
db = client["user_agent_db"]
users_collection = db["users"]
memory_collection = db["user_memory"]

users_collection.create_index([("email", ASCENDING)], unique=True)
memory_collection.create_index([("user_id", ASCENDING)], unique=True)

# --- 3. LOGIQUE IA (AGENT AVEC EXTRACTION JSON) ---
class AIAgent:
    def __init__(self, db_instance):
        self.memory_col = db_instance["user_memory"]
        # On utilise le modèle flash qui est rapide et efficace pour l'extraction
        self.model = genai.GenerativeModel("gemini-2.0-flash")

    def get_memory(self, user_id):
        mem = self.memory_col.find_one({"user_id": ObjectId(user_id)})
        return mem if mem else {"likes": [], "dislikes": []}

    def update_pref(self, user_id, category, items):
        if items:
            self.memory_col.update_one(
                {"user_id": ObjectId(user_id)},
                {"$addToSet": {category: {"$each": items}}}, # $each pour ajouter une liste
                upsert=True
            )

    def extract_info_as_json(self, text):
        """
        Demande à Gemini d'analyser le texte et de renvoyer un JSON strict.
        """
        extraction_prompt = (
            f"Analyse le message suivant de l'utilisateur. Ton but est d'extraire ses goûts (likes) "
            f"et ce qu'il n'aime pas (dislikes) s'ils sont mentionnés explicitement.\n"
            f"Message utilisateur : \"{text}\"\n\n"
            f"Réponds UNIQUEMENT avec un objet JSON valide suivant ce format exact (sans markdown, sans texte autour) :\n"
            f'{{"likes": ["item1", "item2"], "dislikes": ["item3"]}}\n'
            f"Si aucune information n'est trouvée, renvoie des listes vides."
        )

        try:
            # Appel API pour l'extraction
            response = self.model.generate_content(extraction_prompt)
            raw_text = response.text.strip()
            
            # Nettoyage au cas où Gemini ajoute des balises markdown ```json ... ```
            clean_text = re.sub(r'```json\s*|\s*```', '', raw_text)
            
            data = json.loads(clean_text)
            return data
        except Exception as e:
            print(f"Erreur extraction JSON : {e}")
            return {"likes": [], "dislikes": []}

    def process_message(self, user_id, text):
        system_note = ""
        
        # 1. Étape d'Analyse (Extraction JSON)
        extracted_data = self.extract_info_as_json(text)
        
        new_likes = extracted_data.get("likes", [])
        new_dislikes = extracted_data.get("dislikes", [])
        
        # 2. Mise à jour de la DB
        if new_likes:
            self.update_pref(user_id, "likes", new_likes)
            system_note += f"(J'ai noté que vous aimez : {', '.join(new_likes)}) "
        
        if new_dislikes:
            self.update_pref(user_id, "dislikes", new_dislikes)
            system_note += f"(J'ai noté que vous n'aimez pas : {', '.join(new_dislikes)})"

        # 3. Récupération du contexte complet (mémoire mise à jour)
        mem = self.get_memory(user_id)
        all_likes = ", ".join(mem.get("likes", []))
        all_dislikes = ", ".join(mem.get("dislikes", []))
        
        # 4. Génération de la réponse conversationnelle
        context_prompt = (
            f"Tu es un assistant personnel intelligent.\n"
            f"CONTEXTE MÉMOIRE SUR L'UTILISATEUR :\n"
            f"- Aime : {all_likes if all_likes else 'Rien de connu'}\n"
            f"- N'aime pas : {all_dislikes if all_dislikes else 'Rien de connu'}\n\n"
            f"Consigne : Réponds naturellement au dernier message de l'utilisateur. "
            f"Utilise le contexte mémoire pour personnaliser ta réponse si pertinent."
        )
        
        full_prompt = f"{context_prompt}\n\nUtilisateur: {text}\nAssistant:"
        
        try:
            response = self.model.generate_content(full_prompt)
            final_response = response.text
            
            # On ajoute une petite note système au début si on a appris quelque chose
            # (Optionnel, mais utile pour le debug visuel dans le chat)
            if system_note:
                final_response = f"_{system_note}_\n\n{final_response}"
                
            return final_response
        except Exception as e:
            print(f"Erreur réponse Gemini : {e}")
            return "Désolé, je rencontre un problème technique."

# Initialisation de l'agent
agent = AIAgent(db)

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
    """Route de chat avec IA 'augmentée' par l'extraction JSON"""
    response = agent.process_message(current_user["id"], payload.message)
    return {"response": response}