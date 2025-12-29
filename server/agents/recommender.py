import os
from openai import OpenAI

class RecommenderAgent:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            # api_key=os.getenv("GROQ_API_KEY")
            api_key=os.getenv("OPENAI_API_KEY")
        )


    def recommend(self, query, user_prefs):
        try:
            response = self.client.chat.completions.create(
                # model="llama-3.3-70b-versatile",
                 model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": f"Tu es un Recommandeur Expert. Profil utilisateur : {user_prefs}. Suggère 3 produits adaptés."},
                    {"role": "user", "content": query}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Erreur Recommender: {e}"