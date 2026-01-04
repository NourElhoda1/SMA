import os
import json
import re
import datetime
from bson import ObjectId

from crewai import Agent, Task, Crew, Process, LLM
from agents.tools import SearchTool
from agents.comparator import ComparatorAgent
from agents.buyer import BuyerAgent
from agents.recommender import RecommenderAgent  # Import it


class UserAgent:
    def __init__(self, db_instance):
        self.memory_col = db_instance["user_memory"]
        self.history_col = db_instance["chat_history"]
        self.comparator_agent = ComparatorAgent()
        self.buyer = BuyerAgent()
        self.recommender_agent = RecommenderAgent()  # ✅ ADD THIS LINE

        self.llm = LLM(
            model="gpt-4o-mini",
            api_key=os.getenv("OPENAI_API_KEY")
        )

        # Agent Acheteur
        self.buyer_agent_crew = Agent(
            role='Buyer Agent',
            goal='Rechercher les prix exacts et les liens produits sur Google Shopping.',
            backstory="Tu es un expert qui sait trouver les meilleures offres en ligne.",
            tools=[SearchTool()],
            max_iter=5,
            llm=self.llm,
            verbose=False,
            allow_delegation=False
        )

        # Agent recommender
        self.recommender_agent_crew = Agent(
            role='Recommender Agent',
            goal='Analyser les besoins et proposer les meilleurs choix.',
            backstory="Tu es un conseiller personnel qui aide l'utilisateur à choisir le bon produit.",
            llm=self.llm,
            max_iter=5,
            verbose=True,
            allow_delegation=True
        )

    def get_memory(self, user_id):
        mem = self.memory_col.find_one({"user_id": ObjectId(user_id)})
        
        if not mem:
            return {"likes": [], "dislikes": []}
        
        # ✅ Remove MongoDB-specific fields that cause JSON serialization issues
        clean_mem = {
            "likes": mem.get("likes", []),
            "dislikes": mem.get("dislikes", [])
        }
        
        return clean_mem

    def update_pref(self, user_id, category, items):
        if items:
            self.memory_col.update_one(
                {"user_id": ObjectId(user_id)},
                {"$addToSet": {category: {"$each": items}}}, 
                upsert=True
            )

    def save_message(self, user_id, role, content):
        self.history_col.insert_one({
            "user_id": ObjectId(user_id),
            "role": role,
            "content": content,
            "timestamp": datetime.datetime.utcnow()
        })
    
    def get_recent_history(self, user_id, limit=5):
        cursor = self.history_col.find({"user_id": ObjectId(user_id)}).sort("timestamp", -1).limit(limit)
        return [{"role": m["role"], "content": m["content"]} for m in list(cursor)[::-1]]

    def process_message(self, user_id, text):
        self.save_message(user_id, "user", text)
        mem = self.get_memory(user_id)
        history = self.get_recent_history(user_id)
        
        # ✅ Get products FIRST
        apify_data = self.buyer.search(text)
        products = apify_data.get("results", [])
        print(f"📦 Products from Apify: {len(products)}")

        # Handle comparison requests
        if "compare" in text.lower() or "meilleur prix" in text.lower():
            if not products:
                response = {
                    "query": text,
                    "error": "No products found to compare"
                }
            else:
                ranked = self.comparator_agent.compare(products)
                response = {
                    "query": text,
                    "best_value": ranked[:5]
                }
            
            self.save_message(user_id, "assistant", str(response))
            return response

        # ✅ Generate recommendation (now products exists)
        recommendation = self.recommender_agent.recommend(
            query=text,
            products=products,
            user_prefs=mem
        )
        
        self.save_message(user_id, "assistant", recommendation)
        return recommendation