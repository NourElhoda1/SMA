# agents/comparator_tool.py

import json
from crewai.tools import tool
from agents.comparator import ComparatorAgent

_comparator = ComparatorAgent()

@tool("compare_products")
def compare_products(products: str) -> str:
    """
    Compare et classe une liste de produits.

    Input: JSON string d'une liste de produits
    Output: JSON string classé par score décroissant
    """
    try:
        products_list = json.loads(products)

        if not isinstance(products_list, list):
            raise ValueError("Input must be a list of products")

        ranked = _comparator.compare(products_list)

        return json.dumps(ranked, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({
            "error": "Comparator tool failed",
            "details": str(e)
        })
