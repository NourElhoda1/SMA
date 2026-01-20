class NegotiationEngine:
    """
    Negotiation engine to simulate price negotiation for a list of products
    based on user constraints (budget, priority). Handles string prices safely.
    """

    def __init__(self, max_rounds=5, price_tolerance=0.10):
        """
        :param max_rounds: Maximum negotiation rounds per product
        :param price_tolerance: Tolerance factor over budget for negotiation
        """
        self.max_rounds = max_rounds
        self.price_tolerance = price_tolerance

    def negotiate(self, products, user_constraints):
        """
        Simulate negotiation for a list of products.

        :param products: List of dicts with at least 'title' and 'price' or 'extracted_price'
        :param user_constraints: Dict with at least 'budget' key
        :return: List of standardized dicts with negotiation results
        """
        results = []
        budget = user_constraints.get("budget", float('inf'))

        for product in products:
            price = product.get("price") or product.get("extracted_price")
            if price is None:
                continue

            try:
                price = float(str(price).replace("$", "").replace(",", ""))
            except Exception:
                continue 

            counter_offer = price
            rounds = 0

            while rounds < self.max_rounds:
                rounds += 1
                if counter_offer <= budget * (1 + self.price_tolerance):
                    break
                counter_offer *= 0.97 

            acceptance_probability = min(int((budget / counter_offer) * 100), 100)

            results.append({
                "title": product.get("title", "N/A"),
                "listed_price": price,
                "price": price,
                "counter_offer": round(counter_offer, 2),
                "acceptance_probability": acceptance_probability,
                "strategy": "Balanced negotiation based on market flexibility",
                "link": product.get("link", "#")
            })

        return results
