import os
import json
import re
import datetime
from bson import ObjectId
from agents.negotiation_engine import NegotiationEngine
from agents.buyer import BuyerAgent
from agents.DealHunterAgent import DealHunterAgent
from crewai import Agent, Task, Crew, Process, LLM
from agents.tools import SearchTool
from typing import List, Dict, Any


class UserAgent:
    """
    ORCHESTRATOR AGENT
    Manages all other agents and coordinates the multi-agent workflow
    """
    
    def __init__(self, db_instance):
        self.db = db_instance
        self.memory_col = db_instance["user_memory"]
        self.history_col = db_instance["chat_history"]
        self.llm = LLM(
            model="gpt-4o-mini",
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.greetings = [
            'hi', 'hello', 'hey', 'bonjour', 'salut', 'coucou',
            'good morning', 'good afternoon', 'good evening',
            'how are you', 'comment ça va', 'ça va',
            'whats up', "what's up", 'yo', 'sup'
        ]
        self.conversational_patterns = [
            'thank', 'thanks', 'merci', 'thx',
            'bye', 'goodbye', 'au revoir', 'ciao',
            'help', 'aide', 'what can you do',
            'who are you', 'tu es qui',
            'how does this work', 'comment ça marche'
        ]
        self.shopping_triggers = [
            'buy', 'purchase', 'search', 'find', 'show', 'get', 'need', 'want',
            'looking for', 'price', 'cost', 'deal', 'discount', 'cheap',
            'acheter', 'chercher', 'trouver', 'prix', 'coût', 'promotion',
            'phone', 'laptop', 'computer', 'tablet', 'watch', 'headphones',
            'airpods', 'iphone', 'macbook', 'ipad', 'tv', 'camera',
            'téléphone', 'ordinateur', 'tablette', 'montre', 'écouteurs'
        ]
        
        
        # Buyer Agent 
        self.buyer_agent_instance = BuyerAgent()
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

        # Negotiator Agent 
        self.negotiation_engine = NegotiationEngine()
        self.negotiator_agent = Agent(
            role="Negotiator Agent",
            goal="Filter buyer results and select the best deal under user constraints.",
            backstory=(
                "You are a strict negotiator. "
                "You NEVER search for products. "
                "You ONLY analyze the provided product list. "
                "You discard unrealistic prices. "
                "You respect budget and value."
            ),
            tools=[],
            llm=self.llm,
            max_iter=2,
            verbose=True,
            allow_delegation=False
        )

        # Recommender Agent 
        self.recommender_agent_crew = Agent(
            role='Recommender Agent',
            goal='Analyser les besoins et proposer les meilleurs choix.',
            backstory="Tu es un conseiller personnel qui aide l'utilisateur à choisir le bon produit selon ses goûts.",
            llm=self.llm,
            max_iter=3,
            verbose=True,
            allow_delegation=True
        )

        # Deal Hunter Agent 
        self.deal_hunter = DealHunterAgent(
            db_instance=db_instance,
            buyer_agent=self.buyer_agent_instance,
            user_agent=self
        )
        
        print("✅  UserAgent initialized with all sub-agents:")
        print("   - BuyerAgent (Product Search)")
        print("   - NegotiatorAgent (Price Negotiation)")
        print("   - RecommenderAgent (Recommendations)")
        print("   - DealHunterAgent (Deals & Coupons)")
    
    def detect_intent(self, text: str) -> str:
        """
        Detect user intent: greeting, conversational, or shopping
        Returns: 'greeting', 'conversational', or 'shopping'
        """
        text_lower = text.lower().strip()
        words = text_lower.split()
        text_clean = re.sub(r'[^\w\s]', '', text_lower)
        
        if len(words) <= 3:
            for greeting in self.greetings:
                if text_clean == greeting or text_clean.startswith(greeting + ' '):
                    return 'greeting'
        
        if text_clean in self.greetings:
            return 'greeting'
        
        if any(pattern in text_lower for pattern in self.conversational_patterns):
            if not any(trigger in text_lower for trigger in self.shopping_triggers):
                return 'conversational'
        
        if any(trigger in text_lower for trigger in self.shopping_triggers):
            return 'shopping'
        
        if len(words) < 3:
            return 'conversational'
        
        return 'shopping'

    def handle_greeting(self, user_id: str, text: str) -> str:
        """Handle greeting messages"""
        mem = self.get_memory(user_id)
        
        greetings_responses = [
            f"Hello! 👋 Nice to see you! I'm your AI shopping assistant. What can I help you find today?",
            f"Hi there! 😊 I'm here to help you find the best deals. What are you looking for?",
            f"Hey! Welcome back! Ready to find some amazing products?",
            f"Bonjour! 🛍️ I can help you search for products, find deals, and negotiate prices. What interests you?"
        ]
        
        import random
        response = random.choice(greetings_responses)
        if mem.get('likes'):
            response += f"\n\nI remember you like: {', '.join(mem['likes'][:3])}. Want to search for something related?"
        
        return response

    def handle_conversational(self, user_id: str, text: str) -> str:
        """Handle conversational (non-shopping) messages"""
        text_lower = text.lower()
        if any(word in text_lower for word in ['thank', 'merci', 'thx']):
            return "You're welcome! 😊 Let me know if you need anything else!"
        
        if any(word in text_lower for word in ['bye', 'goodbye', 'au revoir']):
            return "Goodbye! 👋 Come back anytime you need help finding great deals!"
        
        if any(word in text_lower for word in ['help', 'aide', 'what can you do']):
            return """I'm your AI shopping assistant! Here's what I can do:

🔍 **Search Products** - Find products on Google Shopping
💰 **Find Deals** - Discover coupons, vouchers, and promotions
🤝 **Negotiate Prices** - Suggest counter-offers and best deals
📊 **Smart Recommendations** - Personalized suggestions based on your preferences
📚 **Remember Preferences** - Learn what you like and dislike

Just tell me what you're looking for! For example:
- "Find me wireless headphones under $100"
- "I need a new laptop for gaming"
- "Show me iPhone deals"
"""
        
        if any(word in text_lower for word in ['who are you', 'tu es qui']):
            return """I'm your AI Shopping Assistant! 🤖

I use multiple AI agents working together:
- 🔍 **Buyer Agent** - Searches for products
- 🎯 **Deal Hunter** - Finds coupons and promotions
- 🤝 **Negotiator** - Analyzes prices
- 💡 **Recommender** - Gives personalized advice

I'm here to make your shopping easier and help you find the best deals!
"""
        
        return "I'm here to help you shop! Tell me what you're looking for, and I'll find the best deals for you. 🛍️"

    
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
            "user_id": ObjectId(user_id),
            "role": role,
            "content": content,
            "timestamp": datetime.datetime.utcnow()
        })

    def get_recent_history(self, user_id, limit=5):
        cursor = self.history_col.find({"user_id": ObjectId(user_id)}).sort("timestamp", -1).limit(limit)
        return [{"role": m["role"], "content": m["content"]} for m in list(cursor)[::-1]]
    
    @staticmethod
    def format_negotiation_result(negotiated: Dict[str, Any]) -> str:
        return (
            f"🛒 **Product:** {negotiated.get('title', 'N/A')}\n"
            f"💰 **Listed price:** ${negotiated.get('listed_price', negotiated.get('price', 'N/A'))}\n"
            f"🤝 **Suggested counter-offer:** ${negotiated.get('counter_offer', 'N/A')}\n"
            f"📊 **Acceptance probability:** {negotiated.get('acceptance_probability', 'N/A')}%\n"
            f"🧠 **Strategy:** {negotiated.get('strategy', 'N/A')}\n"
            f"🔗 **Buy link:** {negotiated.get('link', 'N/A')}\n"
        )

    @staticmethod
    def format_deal_result(deal: Dict[str, Any]) -> str:
        deal_type = deal.get('type', 'deal').upper()
        source = deal.get('source', 'Unknown')
        
        result = f"### 🎯 {deal_type} from {source}\n\n"
        
        if deal.get('code'):
            result += f"**📋 Code:** `{deal['code']}`\n"
        
        if deal.get('name'):
            result += f"**📌 Name:** {deal['name']}\n"
        
        if deal.get('discount'):
            result += f"**💰 Discount:** {deal['discount']}\n"
        
        if deal.get('description'):
            result += f"**ℹ️ Description:** {deal['description']}\n"
        
        if deal.get('expires') or deal.get('expiration_date'):
            expiry = deal.get('expires') or deal.get('expiration_date')
            result += f"**⏰ Expires:** {expiry}\n"
        
        if deal.get('relevance_score'):
            score = deal['relevance_score']
            result += f"**⭐ Relevance:** {score:.0%}\n"
        
        if deal.get('url') or deal.get('redemption_url'):
            url = deal.get('url') or deal.get('redemption_url')
            result += f"**🔗 Link:** {url}\n"
        
        return result + "\n"

    
    def handle_deal_commands(self, user_id: str, text: str) -> str:
        """Handle special deal-related commands"""
        text_lower = text.lower()
        
        if any(phrase in text_lower for phrase in ["show deals", "my deals", "active deals", "what deals"]):
            deals = self.deal_hunter.get_active_deals(user_id, limit=10)
            
            if not deals:
                return "### 🎯 No Active Deals\n\nI haven't found any deals yet. Try searching for products to discover deals!"
            
            response = f"### 🎯 Your Active Deals ({len(deals)} found)\n\n"
            for deal in deals:
                response += self.format_deal_result(deal)
            
            return response
   
        if any(phrase in text_lower for phrase in ["show alerts", "deal alerts", "my alerts"]):
            alerts = list(self.db["deal_alerts"].find({
                "user_id": ObjectId(user_id)
            }).sort("timestamp", -1).limit(10))
            
            if not alerts:
                return "### 🔔 No Alerts\n\nYou don't have any deal alerts yet."
            
            response = f"### 🔔 Your Deal Alerts ({len(alerts)} found)\n\n"
            for alert in alerts:
                response += f"**{alert.get('type', 'ALERT')}** - {alert.get('title', 'Deal')}\n"
                response += f"💰 {alert.get('discount', 'N/A')}\n"
                if alert.get('code'):
                    response += f"📋 Code: `{alert['code']}`\n"
                response += f"⏰ {alert.get('timestamp', 'N/A')}\n\n"
            
            return response
        
        voucher_match = re.search(r'validate\s+(?:voucher\s+)?([A-Z0-9]+)', text, re.IGNORECASE)
        if voucher_match:
            code = voucher_match.group(1).upper()
            result = self.deal_hunter.validate_voucher(code, customer_id=user_id)
            
            if result.get('valid'):
                discount = result.get('discount', {})
                return (
                    f"### ✅ Voucher Valid!\n\n"
                    f"**Code:** `{code}`\n"
                    f"**Discount:** {discount.get('text', 'N/A')}\n"
                    f"**Type:** {discount.get('type', 'N/A')}\n"
                )
            else:
                return (
                    f"### ❌ Voucher Invalid\n\n"
                    f"**Code:** `{code}`\n"
                    f"**Reason:** {result.get('reason', 'Not found or expired')}\n"
                )
        
        return None 
    
    def process_message(self, user_id, text):
        """
        🎯 MAIN ORCHESTRATION LOGIC
        Coordinates all agents to process user messages
        """
        self.save_message(user_id, "user", text)
        intent = self.detect_intent(text)
        print(f"🎯 Detected intent: {intent}")
        
        if intent == 'greeting':
            response = self.handle_greeting(user_id, text)
            self.save_message(user_id, "assistant", response)
            print(f"✅ Greeting handled, no product search triggered")
            return response
        
        if intent == 'conversational':
            response = self.handle_conversational(user_id, text)
            self.save_message(user_id, "assistant", response)
            print(f"✅ Conversational message handled, no product search triggered")
            return response

        print(f"🛍️ Shopping intent detected - starting product search workflow")
        
        mem = self.get_memory(user_id)
        history = self.get_recent_history(user_id)

        user_context = (
            f"PROFIL UTILISATEUR :\n- Aime : {mem.get('likes')}\n- Déteste : {mem.get('dislikes')}\n"
            f"HISTORIQUE RÉCENT : {history}\n"
        )

        deal_command_response = self.handle_deal_commands(user_id, text)
        if deal_command_response:
            self.save_message(user_id, "assistant", deal_command_response)
            return deal_command_response

        buyer_results = None
        products_summary = ""
        
        print("🔍 BuyerAgent: Searching for products...")
        buyer_results = self.buyer_agent_crew.tools[0].run(text)

        if buyer_results and buyer_results.get("results"):
            products_summary += "## 🛒 Products Found\n\n"
            for idx, p in enumerate(buyer_results["results"], 1):
                price_str = p.get("price", "N/A")
                products_summary += (
                    f"{idx}. **{p.get('title', 'N/A')}**\n"
                    f"   💰 Price: {price_str}\n"
                    f"   🔗 [Buy here]({p.get('link', '#')})\n\n"
                )

        deals_summary = ""
        
        if buyer_results and buyer_results.get("results"):
            print("🎯 DealHunterAgent: Searching for deals...")
            
            try:
                self.deal_hunter.start_monitoring(
                    user_id=user_id,
                    query=text,
                    duration_hours=24
                )
                print("✅ Background deal monitoring started (24h)")
            except Exception as e:
                print(f"⚠️ Could not start monitoring: {e}")
            
            all_deals = []
            for product in buyer_results["results"][:3]:
                try:
                    product_deals = self.deal_hunter.find_deals_for_product(product)
                    all_deals.extend(product_deals)
                except Exception as e:
                    print(f"⚠️ Error finding deals for product: {e}")
            
            if all_deals:
                deals_summary += "## 🎁 Special Deals & Coupons\n\n"
                sorted_deals = sorted(
                    all_deals, 
                    key=lambda d: d.get('relevance_score', 0), 
                    reverse=True
                )
                for deal in sorted_deals[:5]:
                    deals_summary += self.format_deal_result(deal)

        negotiation_summary = ""
        negotiated_list = []
        
        if buyer_results and buyer_results.get("results"):
            print("🤝 NegotiatorAgent: Evaluating prices...")
            
            for p in buyer_results["results"]:
                raw_price = p.get("price") or p.get("extracted_price")
                try:
                    p["price"] = float(str(raw_price).replace("$", "").replace(",", ""))
                except Exception:
                    p["price"] = None

            negotiated_list = self.negotiation_engine.negotiate(
                buyer_results["results"],
                user_constraints={"budget": 150, "priority": "value"}
            )

            if negotiated_list:
                negotiation_summary += "## 🤝 Negotiation Analysis\n\n"
                for idx, n in enumerate(negotiated_list[:3], 1):  
                    if isinstance(n, dict):
                        negotiation_summary += f"### Option {idx}\n"
                        negotiation_summary += self.format_negotiation_result(n) + "\n"

        print("💡 RecommenderAgent: Generating recommendations...")
        
        task_description = (
            f"{user_context}\n"
            f"USER REQUEST: '{text}'\n\n"
            "MULTI-AGENT PIPELINE:\n"
            "1. ✅ BuyerAgent: Retrieved product listings from Google Shopping\n"
            "2. ✅ DealHunterAgent: Searched for vouchers, coupons, and promotions\n"
            "3. ✅ NegotiatorAgent: Analyzed prices and suggested counter-offers\n"
            "4. 🎯 YOUR TASK: Provide final recommendation\n\n"
        )
        
        if products_summary:
            task_description += f"PRODUCTS FOUND:\n{products_summary}\n\n"
        
        if deals_summary:
            task_description += f"AVAILABLE DEALS:\n{deals_summary}\n\n"
        
        if negotiation_summary:
            task_description += f"NEGOTIATION RESULTS:\n{negotiation_summary}\n\n"
        
        task_description += (
            "Provide a natural, conversational recommendation in Markdown.\n"
            "Highlight the best deal considering:\n"
            "- Product quality and reviews\n"
            "- Available discounts and vouchers\n"
            "- Negotiated prices\n"
            "- User preferences\n\n"
            "End with hidden JSON if learning new preferences:\n"
            "```json {\"new_likes\":[],\"new_dislikes\":[]} ```"
        )

        task = Task(
            description=task_description,
            expected_output="Réponse naturelle en Markdown + JSON caché optionnel",
            agent=self.recommender_agent_crew
        )

        sma_crew = Crew(
            agents=[self.buyer_agent_crew, self.negotiator_agent, self.recommender_agent_crew],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
            max_rpm=10
        )

        print(f"Running CrewAI workflow for: {text}")
        recommender_result = sma_crew.kickoff()
        recommender_text = str(recommender_result)

        final_reply = ""
        
        if deals_summary:
            final_reply += deals_summary + "\n"
        
        if products_summary:
            final_reply += products_summary + "\n"
            
        if negotiation_summary:
            final_reply += negotiation_summary + "\n"
        
        final_reply += "## 💡 Final Recommendation\n\n"
        final_reply += recommender_text

        try:
            clean_json = re.sub(r'```json\s*|\s*```', '', recommender_text.strip())
            match = re.search(r'\{.*\}', clean_json, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                if data.get("new_likes"):
                    self.update_pref(user_id, "likes", data["new_likes"])
                    print(f"Learned new likes: {data['new_likes']}")
                if data.get("new_dislikes"):
                    self.update_pref(user_id, "dislikes", data["new_dislikes"])
                    print(f"Learned new dislikes: {data['new_dislikes']}")
                final_reply = recommender_text.replace(match.group(0), "").replace("```json", "").replace("```", "").strip()
        except Exception as e:
            print(f"JSON parsing error: {e}")

        # Save assistant reply
        self.save_message(user_id, "assistant", final_reply)
        
        print("Message processed successfully")
        return final_reply
    
    
    def get_user_deals(self, user_id: str, limit: int = 10):
        """Public method to get user's active deals"""
        return self.deal_hunter.get_active_deals(user_id, limit)
    
    def get_user_alerts(self, user_id: str, limit: int = 20):
        """Public method to get user's deal alerts"""
        alerts = list(self.db["deal_alerts"].find({
            "user_id": ObjectId(user_id)
        }).sort("timestamp", -1).limit(limit))
        
        for alert in alerts:
            alert["_id"] = str(alert["_id"])
            alert["user_id"] = str(alert["user_id"])
            if "timestamp" in alert:
                alert["timestamp"] = alert["timestamp"].isoformat()
        
        return alerts
    
    def validate_voucher(self, code: str, user_id: str):
        """Public method to validate a voucher"""
        return self.deal_hunter.validate_voucher(code, customer_id=user_id)
    
    def start_deal_monitoring(self, user_id: str, query: str, duration_hours: int = 24):
        """Public method to start deal monitoring"""
        return self.deal_hunter.start_monitoring(user_id, query, duration_hours)