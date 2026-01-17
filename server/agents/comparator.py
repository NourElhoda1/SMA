import re

class ComparatorAgent:
    """
    Classe de comparaison déterministe des produits.
    Aucun raisonnement LLM ici.
    """

    def __init__(self):
        pass

    def _extract_number(self, text):
        if not text:
            return None
        nums = re.findall(r"\d+[.,]?\d*", str(text).replace(",", "."))
        if not nums:
            return None
        try:
            return float(nums[0])
        except ValueError:
            return None

    def compute_total_cost(self, item):
        """
        Calcule le coût total : prix + livraison + frais cachés
        """
        price = self._extract_number(item.get("price"))
        shipping = self._extract_number(item.get("shipping", "0"))
        hidden = self._extract_number(item.get("additionalFees", "0"))

        if price is None:
            return None

        return (price or 0) + (shipping or 0) + (hidden or 0)

    def score_item(self, item):
        """
        Score global combinant :
        - prix (moins cher = meilleur)
        - rating (plus élevé = meilleur)
        - délai de livraison (plus court = meilleur)
        """
        total_cost = self.compute_total_cost(item)
        if total_cost is None or total_cost <= 0:
            return None

        rating = item.get("rating", 0) or 0
        delivery = self._extract_number(item.get("deliveryDays", "0")) or 1

        score = (
            0.6 * (1 / total_cost) +
            0.2 * float(rating) +
            0.2 * (1 / delivery)
        )

        return score

    def compare(self, products):
        """
        Compare une liste de produits et retourne un ranking décroissant.
        """
        scored = []

        for p in products:
            score = self.score_item(p)
            if score is None:
                continue

            scored.append({
                "title": p.get("title"),
                "price": p.get("price"),
                "shipping": p.get("shipping"),
                "rating": p.get("rating"),
                "deliveryDays": p.get("deliveryDays"),
                "link": p.get("link"),
                "score": score
            })

        return sorted(scored, key=lambda x: x["score"], reverse=True)
