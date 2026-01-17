import requests
import os
import time


class BuyerAgent:
    def __init__(self):
        self.api_key = os.getenv("SERPAPI_KEY")
        if not self.api_key:
            raise ValueError("SERPAPI_KEY not set in environment variables")

        self.base_url = "https://serpapi.com/search.json"

    # ✅ REQUIRED by CrewAI SearchGoogleShopping
    def search_products(self, query, max_items=10):
        return self.search(query, max_items)

    def search(self, query, max_items=10, country="us", language="en"):
        results = []
        start = 0

        while len(results) < max_items:
            params = {
                "engine": "google",
                "q": query,
                "tbm": "shop",
                "hl": language,
                "gl": country,
                "api_key": self.api_key,
                "start": start
            }

            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()

            shopping_results = data.get("shopping_results", [])
            if not shopping_results:
                break
            from urllib.parse import quote

            for item in shopping_results:
             raw_link = item.get("product_link", "")
             safe_link = quote(raw_link, safe=":/?=&|,")

             results.append({
             "title": item.get("title"),
             "price": item.get("price"),
             "extracted_price": item.get("extracted_price"),
             "merchant": item.get("merchant"),
             "rating": item.get("rating"),
             "reviews": item.get("reviews"),
             "link": f"<{safe_link}>",   # ✅ FULLY clickable
             "thumbnail": item.get("thumbnail"),
    })

             if len(results) >= max_items:
                    break

            # Pagination
            if "serpapi_pagination" not in data:
                break

            start += 20
            time.sleep(1)  # avoid rate-limit

        return {
            "query": query,
            "results": results
        }
