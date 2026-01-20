from typing import List, Dict, Any
import math


class RecommenderAgent:
    """
    Deterministic negotiation + scoring engine
    """

    def __init__(self, deal_hunter):
        self.deal_hunter = deal_hunter

    def normalize(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized = []

        for p in products:
            price = p.get("extracted_price") or p.get("price")

            try:
                price = float(str(price).replace("$", "").replace(",", ""))
            except:
                price = None

            normalized.append({
                "title": p.get("title"),
                "price": price,
                "rating": float(p["rating"]) if p.get("rating") else None,
                "reviews": p.get("reviews"),
                "merchant": p.get("merchant"),
                "link": p.get("link"),
                "thumbnail": p.get("thumbnail"),
            })

        return normalized
    
        def recommend(self, products: List[Dict]) -> List[Dict]:
            enriched_products = []

            for product in products:
                deals = self.deal_hunter.find_deals_for_product(product)
                product["deals"] = deals
                product["has_deal"] = len(deals) > 0
                enriched_products.append(product)
            enriched_products.sort(key=lambda p: (not p["has_deal"], p.get("price", float("inf"))))

        return enriched_products

    def negotiate(
        self,
        products: List[Dict[str, Any]],
        max_price: float | None = None,
        min_rating: float = 3.5
    ) -> List[Dict[str, Any]]:

        negotiated = []

        for p in products:
            if not p["price"]:
                continue

            score = 0
            score += max(0, 1000 - p["price"])

            if max_price and p["price"] > max_price:
                score -= 500

            if p["rating"]:
                score += p["rating"] * 100
                if p["rating"] < min_rating:
                    score -= 300

            counter_offer = round(p["price"] * 0.93, 2)

            acceptance_prob = min(
                95,
                max(30, int(50 + (score / 40)))
            )

            negotiated.append({
                **p,
                "score": score,
                "listed_price": p["price"],
                "counter_offer": counter_offer,
                "acceptance_probability": acceptance_prob,
                "strategy": "Balanced negotiation based on market flexibility"
            })

        return sorted(negotiated, key=lambda x: x["score"], reverse=True)
