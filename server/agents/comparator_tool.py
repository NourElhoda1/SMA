import json
from crewai.tools import tool
from agents.comparator import ComparatorAgent

_comparator = ComparatorAgent()

@tool("compare_products")
def compare_products(products_json: str) -> str:
    """
    Classe et compare des produits selon prix, note et délai.

    Input (JSON string) :
    [
      {
        "title": "Product name",
        "price": "120€",
        "shipping": "10€",
        "additionalFees": "5€",
        "rating": 4.6,
        "deliveryDays": "3",
        "link": "<https://example.com>"
      }
    ]

    Output :
    JSON string avec produits classés par score décroissant.
    """

    try:
        products = json.loads(products_json)

        if not isinstance(products, list):
            raise ValueError("Input must be a list of products")

        ranked = _comparator.compare(products)

        return json.dumps(
            ranked,
            ensure_ascii=False,
            indent=2
        )

    except Exception as e:
        return json.dumps({
            "error": "Comparator tool failed",
            "details": str(e)
        })
