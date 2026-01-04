import requests
import os
import time


class BuyerAgent:
    def __init__(self):
        self.token = os.getenv("APIFY_TOKEN")
        
        # Use the Google Shopping Apify actor
        self.actor_id = "F1ITW3XNjGuy7ZzcM"  # google-shopping-apify
        
        if not self.token:
            raise ValueError("APIFY_TOKEN is missing from environment variables")
        
        print(f"🔧 Using Apify actor: google-shopping-apify")

    def search(self, query, max_items=10):
        """
        Search Google Shopping via Apify
        """
        try:
            # Start the actor run
            run_url = f"https://api.apify.com/v2/acts/{self.actor_id}/runs?token={self.token}"
            
            payload = {
                "search": query,  # The search query
                "maxItems": max_items,
                "countryCode": "us",
                "languageCode": "en"
            }

            print(f"🔍 Searching Google Shopping for: '{query}'")
            
            run_response = requests.post(run_url, json=payload, timeout=20)
            
            if run_response.status_code != 201:
                print(f"❌ Failed to start actor. Status: {run_response.status_code}")
                print(f"Response: {run_response.text}")
                return {
                    "query": query,
                    "results": [],
                    "error": f"Failed to start actor: {run_response.status_code}"
                }
            
            run_response.raise_for_status()
            run_data = run_response.json()
            run_id = run_data["data"]["id"]
            
            print(f"✅ Actor run started with ID: {run_id}")

            # Wait for the actor to finish
            status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={self.token}"
            start_time = time.time()
            max_wait_time = 90  # 90 seconds timeout

            while True:
                time.sleep(3)  # Check every 3 seconds
                
                status_response = requests.get(status_url, timeout=15)
                status_data = status_response.json()
                status = status_data["data"]["status"]

                print(f"🔄 Actor status: {status}")

                if status == "SUCCEEDED":
                    print("✅ Actor completed successfully")
                    break

                if status in ("FAILED", "ABORTED", "TIMED-OUT"):
                    error_msg = f"Actor run {status}"
                    print(f"❌ {error_msg}")
                    return {
                        "query": query,
                        "results": [],
                        "error": error_msg
                    }

                if time.time() - start_time > max_wait_time:
                    print("❌ Timeout waiting for actor")
                    return {
                        "query": query,
                        "results": [],
                        "error": "Actor run timed out"
                    }

            # Get the results from the dataset
            dataset_id = status_data["data"]["defaultDatasetId"]
            dataset_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={self.token}"

            print(f"📊 Fetching results from dataset: {dataset_id}")
            
            dataset_response = requests.get(dataset_url, timeout=20)
            dataset_response.raise_for_status()
            items = dataset_response.json()

            print(f"📦 Retrieved {len(items)} items from Google Shopping")

            if not items:
                return {
                    "query": query,
                    "results": [],
                    "error": "No products found for this query"
                }

            # Normalize the data structure
            results = []
            for item in items[:max_items]:
                # Different actors have different field names, adjust as needed
                results.append({
                    "title": item.get("title") or item.get("name", ""),
                    "price": item.get("price") or item.get("priceValue", 0),
                    "currency": item.get("currency", "USD"),
                    "url": item.get("url") or item.get("link", ""),
                    "source": item.get("source") or item.get("seller", ""),
                    "rating": item.get("rating", 0),
                    "reviews": item.get("reviews") or item.get("reviewsCount", 0),
                    "image": item.get("image") or item.get("thumbnail", ""),
                    "availability": item.get("availability", "In Stock")
                })

            return {
                "query": query,
                "results": results,
                "error": None
            }

        except requests.exceptions.RequestException as e:
            print(f"❌ HTTP Error: {str(e)}")
            return {
                "query": query,
                "results": [],
                "error": f"HTTP Error: {str(e)}"
            }
        
        except Exception as e:
            print(f"❌ BuyerAgent error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "query": query,
                "results": [],
                "error": str(e)
            }