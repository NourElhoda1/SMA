from serpapi import GoogleSearch
import os
from dotenv import load_dotenv

load_dotenv()

class BuyerAgent:
    def __init__(self):
        self.api_key = os.getenv("SERPAPI_KEY")
        
    def search_products(self, query, max_price=None):
        print(f"🛒 Buyer Agent cherche : {query}...")
        
        params = {
            "engine": "google_shopping",
            "q": query,
            "api_key": self.api_key,
            "num": 4,
            "gl": "fr", 
            "hl": "fr"
        }

        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            shopping_results = results.get("shopping_results", [])
            
            if not shopping_results:
                return "Aucun produit trouvé sur Google Shopping."

            formatted_response = "Voici les meilleures offres trouvées en ligne :\n"
            for item in shopping_results:
                title = item.get("title")
                price = item.get("price")
                link = item.get("link")
                source = item.get("source")
                
                formatted_response += (
                    f"- **{title}**\n"
                    f"  💰 {price} | Vendeur: {source}\n"
                    f"  🔗 [Voir l'offre]({link})\n\n"
                )
            
            return formatted_response

        except Exception as e:
            return f"Erreur SerpApi : {e}"