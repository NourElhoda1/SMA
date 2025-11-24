import os
from dotenv import load_dotenv
import google.generativeai as genai
from pymongo import MongoClient

# ---------- Setup ----------
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Connect to MongoDB
mongo_client = MongoClient(os.getenv("MONGO_URI"))
db = mongo_client["user_agent_db"]
prefs_collection = db["preferences"]

# ---------- Memory Layer (MongoDB) ----------
def set_pref(key, value):
    prefs_collection.update_one({"key": key}, {"$set": {"value": value}}, upsert=True)

def get_all_prefs():
    prefs = {}
    for item in prefs_collection.find():
        prefs[item["key"]] = item["value"]
    return prefs

# ---------- UserAgent ----------
class UserAgent:
    def __init__(self):
        self.model = genai.GenerativeModel("gemini-2.0-flash")

    def remember(self, text):
        text_lower = text.lower()
        if "i like" in text_lower:
            pref = text_lower.split("i like", 1)[1].strip(". ")
            set_pref("likes", pref)
            return f"Got it! I'll remember you like {pref}."
        elif "my name is" in text_lower:
            name = text_lower.split("my name is", 1)[1].strip(". ")
            set_pref("name", name)
            return f"Nice to meet you, {name.title()}!"
        return None

    def chat(self, text):
        # Check for memory updates
        mem_response = self.remember(text)
        if mem_response:
            return mem_response

        # Retrieve preferences
        prefs = get_all_prefs()
        memory_context = (
            "User preferences:\n" + "\n".join([f"- {k}: {v}" for k, v in prefs.items()])
            if prefs else "No preferences yet."
        )

        # Generate a response
        response = self.model.generate_content(f"{memory_context}\nUser: {text}\nAssistant:")
        return response.text

# ---------- Example CrewAI Setup ----------
# def setup_crewai():
#     buyer = Agent(
#         role="BuyerAgent",
#         goal="Find and compare products or services.",
#         backstory="An expert shopper who knows the best marketplaces and evaluates options objectively."
#     )

#     negotiator = Agent(
#         role="NegotiatorAgent",
#         goal="Negotiate the best terms and prices.",
#         backstory="A skilled dealmaker who handles communication between buyer and seller to reach optimal agreements."
#     )

#     ua_task = Task(
#         description="Handle user requests intelligently and route to the right agent."
#     )

#     crew = Crew(
#         agents=[buyer, negotiator],
#         tasks=[ua_task]
#     )

#     return crew

# ---------- CLI loop ----------
if __name__ == "__main__":
    ua = UserAgent()
    print("🤖 User Agent.")
    print("Type something ('quit' to exit).")

    while True:
        msg = input("You: ")
        if msg.lower() in ["quit", "exit"]:
            break
        reply = ua.chat(msg)
        print("UA:", reply)
