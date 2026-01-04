import requests
import os
import time
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("APIFY_TOKEN")
actor_id = "F1ITW3XNjGuy7ZzcM"  # google-shopping-apify

# Test run
run_url = f"https://api.apify.com/v2/acts/{actor_id}/runs?token={token}"

payload = {
    "search": "laptop",
    "maxItems": 5,
    "countryCode": "us"
}

print("🚀 Starting test...")
response = requests.post(run_url, json=payload)
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")