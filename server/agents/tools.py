import json
from crewai.tools import BaseTool
from agents.buyer import BuyerAgent

class SearchTool(BaseTool):
    name: str = "SearchGoogleShopping"
    description: str = (
        "Utile pour rechercher des produits. Input: une requête simple (ex: 'iphone 15'). "
        "Retourne une liste de produits en format JSON String."
    )

    def _run(self, query: str) -> str:
        buyer = BuyerAgent()
        results = buyer.search(query)
        return json.dumps(results.get("results", []), ensure_ascii=False)