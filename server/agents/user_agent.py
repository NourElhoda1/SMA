import json
import re
import os
from bson import ObjectId
from openai import OpenAI

from agents.recommender import RecommenderAgent
from agents.buyer import BuyerAgent

class UserAgent:
    def __init__(self, db_instance):
        self.memory_col = db_instance["user_memory"]
        
        # Configuration GROQ
        api_key = os.getenv("GROQ_API_KEY")
        self.client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=api_key
        )
        self.model_name = "llama-3.3-70b-versatile" # Modèle puissant et rapide
        
        print(f"🚀 UserAgent initialisé sur Groq ({self.model_name})")
        
        # Initialisation de la Team
        self.buyer = BuyerAgent()
        self.recommender = RecommenderAgent()

    def get_memory(self, user_id):
        mem = self.memory_col.find_one({"user_id": ObjectId(user_id)})
        return mem if mem else {"likes": [], "dislikes": []}

    def update_pref(self, user_id, category, items):
        if items:
            self.memory_col.update_one(
                {"user_id": ObjectId(user_id)},
                {"$addToSet": {category: {"$each": items}}}, 
                upsert=True
            )

    def generate_groq(self, messages):
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"🔥 Erreur Groq : {e}")
            return None

    def process_message(self, user_id, text):
        # 1. Contexte
        mem = self.get_memory(user_id)
        user_prefs_str = f"Aime: {mem.get('likes')}, Déteste: {mem.get('dislikes')}"
        text_lower = text.lower()
        
        agent_response = ""
        agent_name = ""

        # 2. Routing (Logique rapide)
        if any(w in text_lower for w in ["acheter", "prix de", "combien coûte", "trouve moi", "search"]):
            agent_name = "Buyer Agent"
            agent_response = self.buyer.search_products(text)
        elif any(w in text_lower for w in ["recommande", "suggère", "idée cadeau"]):
            agent_name = "Recommender Agent"
            agent_response = self.recommender.recommend(text, user_prefs_str)

        # 3. Synthèse avec Groq
        context_part = ""
        if agent_response:
            context_part = f"RÉSULTAT DE L'EXPERT '{agent_name}' : {agent_response}\n(Utilise ces infos pour répondre)"

        system_prompt = (
            f"Tu es un assistant shopping personnel. Contexte : {user_prefs_str}\n"
            f"TÂCHE : Identifie nouveaux goûts et réponds à l'utilisateur.\n"
            f"FORMAT JSON STRICT : {{ \"new_likes\": [], \"new_dislikes\": [], \"reply\": \"...\" }}"
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{text}\n\n{context_part}"}
        ]

        raw_text = self.generate_groq(messages)
        
        if not raw_text:
            return "Désolé, une erreur technique est survenue."

        # Nettoyage JSON
        try:
            clean_json = re.sub(r'```json\s*|\s*```', '', raw_text.strip())
            match = re.search(r'\{.*\}', clean_json, re.DOTALL)
            if match: clean_json = match.group(0)
            
            data = json.loads(clean_json)
            
            if data.get("new_likes"): self.update_pref(user_id, "likes", data["new_likes"])
            if data.get("new_dislikes"): self.update_pref(user_id, "dislikes", data["new_dislikes"])
            
            return data.get("reply", "Pas de réponse textuelle.")
        except:
            return raw_text 