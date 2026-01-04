from crewai.tools import BaseTool
from agents.buyer import BuyerAgent

class SearchTool(BaseTool):
    name: str = "SearchGoogleShopping"
    description: str = (
        "Utile pour rechercher des prix actuels, des produits et des liens d'achat sur Google Shopping. "
    )

    def _run(self, query: str) -> str:
        buyer = BuyerAgent()
        return buyer.search(query)
