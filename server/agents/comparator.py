import re

class ComparatorAgent:
    def __init__(self):
        pass

    def _extract_number(self, text):
        if not text:
            return None
        nums = re.findall(r"\d+[.,]?\d*", text.replace(",", "."))
        if not nums:
            return None
        return float(nums[0])

    def compute_total_cost(self, item):
        price = self._extract_number(item.get("price"))
        shipping = self._extract_number(item.get("shipping", "0"))
        hidden = self._extract_number(item.get("additionalFees", "0"))

        if price is None:
            return None

        return (price or 0) + (shipping or 0) + (hidden or 0)

    def score_item(self, item):
        total = self.compute_total_cost(item)
        if total is None:
            return None

        rating = item.get("rating", 0)
        delivery = self._extract_number(item.get("deliveryDays", "0"))

        score = (
            0.6 * (1 / total) +      # prix bas = bon
            0.2 * float(rating or 0) +  # bonne évaluation = bon
            0.2 * (1 / (delivery or 1)) # délai court = bon
        )
        return score

    def compare(self, products):
        scored = []
        for p in products:
            score = self.score_item(p)
            if score:
                scored.append({
                    "title": p.get("title"),
                    "price": p.get("price"),
                    "shipping": p.get("shipping"),
                    "rating": p.get("rating"),
                    "score": score
                })

        ranked = sorted(scored, key=lambda x: x["score"], reverse=True)
        return ranked
