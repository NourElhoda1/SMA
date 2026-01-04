class AnalyticsHelper:
    def summarize(self, products):
        if not products:
            return "Aucun produit trouvé."

        avg_price = sum([p.get("price", 0) for p in products if p.get("price")]) / len(products)
        return f"Moyenne de prix estimée: {avg_price:.2f}"
