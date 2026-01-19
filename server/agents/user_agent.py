import os
import json
import re
import datetime
from bson import ObjectId
import threading

from crewai import Agent, Task, Crew, Process, LLM
from agents.tools import SearchTool
from agents.comparator_tool import compare_products
from agents.buyer import BuyerAgent
from agents.comparator import ComparatorAgent
from agents.recommender import RecommenderAgent
from agents.DealHunterAgent import DealHunterAgent


class UserAgent:
    def __init__(self, db_instance):
        self.memory_col = db_instance["user_memory"]
        self.history_col = db_instance["chat_history"]

        # Agents classiques
        self.buyer = BuyerAgent()
        self.recommender_agent = RecommenderAgent()
        
        # Deal Hunter
        self.deal_hunter = DealHunterAgent(db_instance, self.buyer, self)

        # LLM pour CrewAI
        self.llm = LLM(
            model="gpt-4o-mini",
            api_key=os.getenv("OPENAI_API_KEY")
        )

        # Agent Acheteur CrewAI
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

        # Agent Comparator CrewAI
        self.comparator_agent_crew = Agent(
            role='Comparator Agent',
            goal="Classer objectivement les produits reçus en utilisant l'outil de comparaison mathématique.",
            backstory="Tu es un analyste rigoureux. Tu ne fais pas confiance aux mots, seulement aux chiffres. Tu dois utiliser ton outil pour calculer un score précis pour chaque produit.",
            tools=[compare_products],
            max_iter=3,
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )

        # Agent Recommender CrewAI
        self.recommender_agent_crew = Agent(
            role='Recommender Agent',
            goal='Analyser les besoins et proposer les meilleurs choix.',
            backstory="Tu es un conseiller personnel qui aide l'utilisateur à choisir le bon produit.",
            llm=self.llm,
            max_iter=5,
            verbose=True,
            allow_delegation=True
        )

        
    # ---------------------------
    # MÉMOIRE UTILISATEUR
    # ---------------------------
    def get_memory(self, user_id):
        mem = self.memory_col.find_one({"user_id": ObjectId(user_id)})
        return {"likes": [], "dislikes": []} if not mem else {"likes": mem.get("likes", []), "dislikes": mem.get("dislikes", [])}

    def update_pref(self, user_id, category, items):
        if items:
            self.memory_col.update_one(
                {"user_id": ObjectId(user_id)},
                {"$addToSet": {category: {"$each": items}}},
                upsert=True
            )

    # ---------------------------
    # HISTORIQUE CHAT
    # ---------------------------
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

    # ---------------------------
    # INTENTION / EXTRACTION
    # ---------------------------
    def _detect_intent(self, text):
        text_lower = text.lower()
        if any(k in text_lower for k in ["surveille", "alerte", "trouve des promo", "cherche des deals", "trouver coupon"]):
            return "monitor_deals"
        if any(k in text_lower for k in ["mes deals", "deals trouvés", "show deals", "voir promo", "liste coupons"]):
            return "show_deals"
        if any(k in text_lower for k in ["valider coupon", "vérifier code", "check voucher", "code promo valide"]):
            return "validate_voucher"
        if any(k in text_lower for k in ["utiliser coupon", "appliquer code", "redeem voucher", "use promo"]):
            return "redeem_voucher"
        if any(k in text_lower for k in ["compare", "comparer", "meilleur prix", "moins cher"]):
            return "compare"
        return "search"

    def _extract_voucher_code(self, text):
        patterns = [
            r'\b([A-Z0-9]{4,15})\b',
            r'code[:\s]+([A-Z0-9]+)',
            r'coupon[:\s]+([A-Z0-9]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        return None

    # ---------------------------
    # DEALS SUR PRODUITS
    # ---------------------------
    def _apply_deals_to_products(self, products, deals):
        enhanced_products = []
        for product in products:
            product_copy = product.copy()
            applicable_deals = []
            for deal in deals:
                if deal.get("relevance_score", 0) > 0.5:
                    pt = product.get("title", "").lower()
                    dn = deal.get("name", "").lower()
                    dc = deal.get("category", "").lower()
                    if any(word in pt for word in dn.split()) or any(word in pt for word in dc.split()):
                        applicable_deals.append({
                            "code": deal.get("code"),
                            "discount": deal.get("discount"),
                            "source": deal.get("source"),
                            "type": deal.get("type")
                        })
            if applicable_deals:
                product_copy["available_deals"] = applicable_deals
                original_price = product.get("price", 0)
                best_deal = applicable_deals[0]
                if "%" in best_deal.get("discount", ""):
                    percent = int(re.search(r'\d+', best_deal["discount"]).group())
                    discounted_price = original_price * (1 - percent / 100)
                    product_copy["discounted_price"] = round(discounted_price, 2)
                    product_copy["savings"] = round(original_price - discounted_price, 2)
            enhanced_products.append(product_copy)
        return enhanced_products

    # ---------------------------
    # PROCESS CREWAI
    # ---------------------------
    def process_message(self, user_id, text):
        self.save_message(user_id, "user", text)
        mem = self.get_memory(user_id)
        history = self.get_recent_history(user_id)

        # Création du contexte pour CrewAI
        user_context = f"PROFIL UTILISATEUR :\n- Aime : {mem.get('likes')}\n- Déteste : {mem.get('dislikes')}\nHISTORIQUE RÉCENT : {history}\n"

        task = Task(
            description=(
                f"{user_context}\n"
                f"DEMANDE UTILISATEUR : '{text}'\n\n"
                "SUIVRE STRICTEMENT CE PLAN :\n"
                "1. [Buyer Agent] Utilise 'SearchGoogleShopping' pour trouver les produits. Retourne le résultat en JSON brut.\n"
                "2. [Comparator Agent] Prends le JSON du Buyer et utilise ton outil 'compare_products' pour calculer les scores. Retourne la liste triée.\n"
                "3. [Recommender Agent] Prends la liste triée et rédige une réponse conviviale en expliquant pourquoi le premier produit est le meilleur.\n"
                "Réponds en Markdown."
            ),
            expected_output="Une réponse naturelle recommandée basée sur le scoring mathématique.",
            agent=self.recommender_agent_crew 
        )


        sma_crew = Crew(
            agents=[
                self.buyer_agent_crew, 
                self.comparator_agent_crew,
                self.recommender_agent_crew
            ],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
            max_rpm=10
        )

        print(f"🚀 CrewAI traite : {text}")
        result = sma_crew.kickoff()
        raw_text = str(result)
        reply_text = raw_text

        # Extraction JSON caché (préférences utilisateur)
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
