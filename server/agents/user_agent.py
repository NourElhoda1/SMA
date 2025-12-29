import os
import json
import re
import datetime
from bson import ObjectId

from crewai import Agent, Task, Crew, Process, LLM
from agents.tools import SearchTool

class UserAgent:
    def __init__(self, db_instance):
        self.memory_col = db_instance["user_memory"]
        self.history_col = db_instance["chat_history"]
        
        # self.llm = LLM(
        #     model="groq/llama-3.1-8b-instant",
        #     api_key=os.getenv("GROQ_API_KEY")
        # )

        

        self.llm = LLM(
            model="gpt-4o-mini", # <--- CHANGEMENT 1 : Le nom du modèle OpenAI (ou "gpt-3.5-turbo")
            api_key=os.getenv("OPENAI_API_KEY") # <--- CHANGEMENT 2 : La variable d'environnement
        )

        # Agent Acheteur
        self.buyer_agent_crew = Agent(
            role='Buyer Agent',
            goal='Rechercher les prix exacts et les liens produits sur Google Shopping.',
            backstory="Tu es un expert qui sait trouver les meilleures offres en ligne. Tu utilises toujours ton outil de recherche.",
            tools=[SearchTool()],
            max_iter=3,
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )

        # Agent recommender
        self.recommender_agent_crew = Agent(
            role='Recommender Agent',
            goal='Analyser les besoins et proposer les meilleurs choix.',
            backstory="Tu es un conseiller personnel qui aide l'utilisateur à choisir le bon produit selon ses goûts.",
            llm=self.llm,
            max_iter=3,
            verbose=True,
            allow_delegation=True
        )

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

    def save_message(self, user_id, role, content):
        self.history_col.insert_one({
            "user_id": ObjectId(user_id), "role": role, "content": content, "timestamp": datetime.datetime.utcnow()
        })
    
    def get_recent_history(self, user_id, limit=5):
        cursor = self.history_col.find({"user_id": ObjectId(user_id)}).sort("timestamp", -1).limit(limit)
        return [{"role": m["role"], "content": m["content"]} for m in list(cursor)[::-1]]

    # --- Exécution CrewAI ---
    def process_message(self, user_id, text):
        self.save_message(user_id, "user", text)
        mem = self.get_memory(user_id)
        history = self.get_recent_history(user_id)
        
        user_context = (
            f"PROFIL UTILISATEUR :\n- Aime : {mem.get('likes')}\n- Déteste : {mem.get('dislikes')}\n"
            f"HISTORIQUE RÉCENT : {history}\n"
        )

        task = Task(
            description=(
                f"{user_context}\n"
                f"DEMANDE : '{text}'\n"
                "1. Si l'utilisateur veut acheter ou voir des prix -> Demande au Buyer Agent de chercher.\n"
                "2. Si l'utilisateur veut un conseil -> Analyse et propose des idées.\n"
                "3. Réponds en Markdown.\n"
                "IMPORTANT : Ajoute ce JSON caché à la fin si tu apprends de nouveaux goûts : ```json { \"new_likes\": [], \"new_dislikes\": [] } ```"
            ),
            expected_output="Réponse textuelle naturelle + JSON caché optionnel.",
            agent=self.recommender_agent_crew 
        )

        sma_crew = Crew(
            agents=[self.buyer_agent_crew, self.recommender_agent_crew],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
            max_rpm=10
        )

        print(f"🚀 CrewAI (Recommender + Buyer) traite : {text}")
        result = sma_crew.kickoff()
        
        raw_text = str(result)
        reply_text = raw_text

        try:
            clean_json = re.sub(r'```json\s*|\s*```', '', raw_text.strip())
            match = re.search(r'\{.*\}', clean_json, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                if data.get("new_likes"): self.update_pref(user_id, "likes", data["new_likes"])
                if data.get("new_dislikes"): self.update_pref(user_id, "dislikes", data["new_dislikes"])
                reply_text = raw_text.replace(match.group(0), "").replace("```json", "").replace("```", "").strip()
        except:
            pass

        self.save_message(user_id, "assistant", reply_text)
        return reply_text