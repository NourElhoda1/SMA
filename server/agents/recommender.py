import os
from openai import OpenAI
import json
from bson import ObjectId

class RecommenderAgent:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )

    def recommend(self, query, products, user_prefs):
        try:
            if not products or len(products) == 0:
                return "❌ Aucun produit trouvé pour votre recherche."

            # Clean and structure the product data
            clean_products = []
            for p in products[:10]:
                clean_products.append({
                    "title": p.get('title', 'N/A'),
                    "price": p.get('price', 0),
                    "currency": p.get('currency', 'USD'),
                    "seller": p.get('source', 'N/A'),
                    "rating": p.get('rating', 0),
                    "reviews": p.get('reviews', 0),
                    "url": p.get('url', 'N/A'),
                    "availability": p.get('availability', 'In Stock')
                })

            # ✅ Clean user_prefs to remove ObjectId and make it JSON-serializable
            clean_prefs = self._clean_mongo_data(user_prefs)

            print(f"📝 Analyzing {len(clean_products)} products")
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.7,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Tu es un expert en recommandation de produits e-commerce.\n\n"
                            "RÈGLES IMPORTANTES:\n"
                            "1. Tu as accès à des données RÉELLES de produits\n"
                            "2. Analyse TOUS les produits fournis\n"
                            "3. Recommande les 3-5 meilleurs en fonction de:\n"
                            "   - Rapport qualité/prix\n"
                            "   - Notes et avis clients\n"
                            "   - Réputation du vendeur\n"
                            "   - Disponibilité\n"
                            "4. Sois spécifique: mentionne les prix exacts et les liens\n"
                            "5. Explique pourquoi tu recommandes chaque produit\n\n"
                            f"Profil utilisateur: {json.dumps(clean_prefs, ensure_ascii=False)}\n"
                        )
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Requête: {query}\n\n"
                            f"Produits disponibles:\n```json\n{json.dumps(clean_products, indent=2, ensure_ascii=False)}\n```\n\n"
                            "Analyse ces produits et recommande-moi les meilleures options."
                        )
                    }
                ],
                max_tokens=1500
            )

            recommendation = response.choices[0].message.content
            
            # Add a summary at the end
            valid_prices = [p['price'] for p in clean_products if isinstance(p['price'], (int, float)) and p['price'] > 0]
            avg_price = sum(valid_prices) / len(valid_prices) if valid_prices else 0
            
            summary = (
                f"\n\n---\n"
                f"📊 {len(clean_products)} produits analysés pour: '{query}'\n"
            )
            
            if avg_price > 0:
                summary += f"💰 Prix moyen: {avg_price:.2f} USD"
            
            return recommendation + summary

        except Exception as e:
            print(f"❌ Erreur Recommender: {e}")
            import traceback
            traceback.print_exc()
            return f"Erreur: {e}"

    def _clean_mongo_data(self, data):
        """
        Recursively clean MongoDB data to make it JSON serializable
        Converts ObjectId to string and handles nested structures
        """
        if isinstance(data, dict):
            return {k: self._clean_mongo_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._clean_mongo_data(item) for item in data]
        elif isinstance(data, ObjectId):
            return str(data)
        else:
            return data