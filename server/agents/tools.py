from crewai.tools import BaseTool
from agents.buyer import BuyerAgent


class SearchTool(BaseTool):
    name: str = "SearchGoogleShopping"
    description: str = (
        "Utile pour rechercher des produits sur Google Shopping. "
        "Input: une requête simple (ex: 'iphone 15'). "
        "Retourne un dictionnaire Python contenant {query, results}."
    )

    def _run(self, query: str):
        buyer = BuyerAgent()
        return buyer.search(query)
