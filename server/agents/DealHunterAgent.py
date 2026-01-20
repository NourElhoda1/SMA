import os
import time
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from bson import ObjectId
import threading
from queue import Queue
import base64

class DealHunterAgent:
    """
    Agent qui surveille les coupons, promotions et bundles via Voucherify API
    et alerte le BuyerAgent ou le UserAgent
    """
    
    def __init__(self, db_instance, buyer_agent, user_agent):
        self.db = db_instance
        self.deals_col = db_instance["deals"]
        self.alerts_col = db_instance["deal_alerts"]
        self.buyer_agent = buyer_agent
        self.user_agent = user_agent
        self.voucherify_app_id = os.getenv("VOUCHERIFY_APP_ID")
        self.voucherify_secret_key = os.getenv("VOUCHERIFY_SECRET_KEY")
        
        if not self.voucherify_app_id or not self.voucherify_secret_key:
            raise ValueError("VOUCHERIFY_APP_ID and VOUCHERIFY_SECRET_KEY must be set")
        
        credentials = f"{self.voucherify_app_id}:{self.voucherify_secret_key}"
        self.voucherify_auth = base64.b64encode(credentials.encode()).decode()
        self.voucherify_base_url = "https://api.voucherify.io/v1"
        self.deal_queue = Queue()
        self.IMMEDIATE_ALERT_THRESHOLD = 0.8
        self.BUYER_NOTIFY_THRESHOLD = 0.5
        
        print("Deal Hunter Agent initialized with Voucherify API")

    def _get_voucherify_headers(self):
        """
        Retourne les headers pour l'API Voucherify
        """
        return {
            "Authorization": f"Basic {self.voucherify_auth}",
            "Content-Type": "application/json",
            "X-App-Id": self.voucherify_app_id,
            "X-App-Token": self.voucherify_secret_key
        }

    def start_monitoring(self, user_id, query, duration_hours=24):
        """
        Lance la surveillance des deals pour une requête utilisateur
        """
        monitoring_doc = {
            "user_id": ObjectId(user_id),
            "query": query,
            "started_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(hours=duration_hours),
            "active": True,
            "deals_found": 0
        }
        
        result = self.deals_col.insert_one(monitoring_doc)
        monitoring_id = result.inserted_id
        
        print(f"Starting deal monitoring for '{query}' (duration: {duration_hours}h)")
        
        
        thread = threading.Thread(
            target=self._monitor_loop,
            args=(str(monitoring_id), user_id, query, duration_hours),
            daemon=True
        )
        thread.start()
        
        return str(monitoring_id)

    def _monitor_loop(self, monitoring_id, user_id, query, duration_hours):
        """
        Boucle de surveillance continue
        """
        end_time = datetime.utcnow() + timedelta(hours=duration_hours)
        check_interval = 300
        
        while datetime.utcnow() < end_time:
            try:
                vouchers = self._search_voucherify_vouchers(query)
                campaigns = self._search_voucherify_campaigns(query)
                promotions = self._search_promotions(query)
                bundles = self._detect_bundles(query)
                
                all_deals = vouchers + campaigns + promotions + bundles
                
                for deal in all_deals:
                    self._process_deal(deal, user_id, query)
                
                self.deals_col.update_one(
                    {"_id": ObjectId(monitoring_id)},
                    {"$inc": {"deals_found": len(all_deals)}}
                )
                
                print(f"Deal scan complete for '{query}': {len(all_deals)} deals found")
                
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                import traceback
                traceback.print_exc()
            
            time.sleep(check_interval)
        
        self.deals_col.update_one(
            {"_id": ObjectId(monitoring_id)},
            {"$set": {"active": False}}
        )
        print(f"Monitoring expired for '{query}'")

    def _search_voucherify_vouchers(self, query) -> List[Dict]:
        """
        Recherche de vouchers via Voucherify API
        """
        vouchers = []
        
        try:
            url = f"{self.voucherify_base_url}/vouchers"
            
            params = {
                "limit": 20,
                "filters": {
                    "junction": "AND",
                    "conditions": [
                        {
                            "conditions": {
                                "$is": ["ACTIVE"]
                            }
                        }
                    ]
                }
            }
            
            print(f"Searching Voucherify vouchers...")
            
            response = requests.get(
                url,
                headers=self._get_voucherify_headers(),
                params={"limit": 20},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                
                for voucher in data.get("vouchers", []):
                    voucher_code = voucher.get("code", "")
                    voucher_name = voucher.get("name", "")
                    category = voucher.get("category", "")
                    
                    search_text = f"{voucher_code} {voucher_name} {category}".lower()
                    
                    discount_info = self._extract_discount_info(voucher)
                    
                    vouchers.append({
                        "type": "voucher",
                        "source": "Voucherify",
                        "code": voucher_code,
                        "name": voucher_name,
                        "category": category,
                        "discount": discount_info["text"],
                        "discount_amount": discount_info["amount"],
                        "discount_type": discount_info["type"],
                        "description": voucher.get("metadata", {}).get("description", ""),
                        "expires": voucher.get("expiration_date", ""),
                        "active": voucher.get("active", False),
                        "redemption_url": voucher.get("redemption", {}).get("url", ""),
                        "raw_data": voucher
                    })
            
            else:
                print(f"Voucherify API error: {response.status_code}")
                print(f"Response: {response.text}")
            
            print(f"Found {len(vouchers)} vouchers from Voucherify")
            
        except Exception as e:
            print(f"Error fetching Voucherify vouchers: {e}")
            import traceback
            traceback.print_exc()
        
        return vouchers

    def _search_voucherify_campaigns(self, query) -> List[Dict]:
        """
        Recherche de campagnes/promotions via Voucherify API
        """
        campaigns = []
        
        try:
            url = f"{self.voucherify_base_url}/campaigns"
            
            print(f"Searching Voucherify campaigns...")
            
            response = requests.get(
                url,
                headers=self._get_voucherify_headers(),
                params={"limit": 20},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                
                for campaign in data.get("campaigns", []):
                    campaign_name = campaign.get("name", "")
                    campaign_type = campaign.get("campaign_type", "")
                    voucher_data = campaign.get("voucher", {})
                    discount_info = self._extract_discount_info(voucher_data)
                    
                    campaigns.append({
                        "type": "campaign",
                        "source": "Voucherify",
                        "name": campaign_name,
                        "campaign_type": campaign_type,
                        "discount": discount_info["text"],
                        "discount_amount": discount_info["amount"],
                        "discount_type": discount_info["type"],
                        "description": campaign.get("description", ""),
                        "start_date": campaign.get("start_date", ""),
                        "expiration_date": campaign.get("expiration_date", ""),
                        "active": campaign.get("active", False),
                        "vouchers_count": campaign.get("vouchers_count", 0),
                        "raw_data": campaign
                    })
            
            else:
                print(f"Voucherify Campaigns API error: {response.status_code}")

            print(f"Found {len(campaigns)} campaigns from Voucherify")

        except Exception as e:
            print(f"Error fetching Voucherify campaigns: {e}")
            import traceback
            traceback.print_exc()
        
        return campaigns

    def _extract_discount_info(self, voucher_data: Dict) -> Dict:
        """
        Extrait les informations de réduction d'un voucher Voucherify
        """
        discount = voucher_data.get("discount", {})
        
        discount_type = discount.get("type", "UNKNOWN")
        discount_amount = 0
        discount_text = "Discount available"
        
        if discount_type == "PERCENT":
            percent_off = discount.get("percent_off", 0)
            discount_amount = percent_off
            discount_text = f"{percent_off}% OFF"
            
        elif discount_type == "AMOUNT":
            amount_off = discount.get("amount_off", 0) / 100  
            discount_amount = amount_off
            discount_text = f"${amount_off:.2f} OFF"
            
        elif discount_type == "UNIT":
            unit_off = discount.get("unit_off", 0)
            unit_type = discount.get("unit_type", "item")
            discount_text = f"{unit_off} {unit_type} FREE"
            
        elif discount_type == "FIXED":
            fixed_amount = discount.get("fixed_amount", 0) / 100
            discount_text = f"Fixed price: ${fixed_amount:.2f}"
        
        return {
            "type": discount_type,
            "amount": discount_amount,
            "text": discount_text
        }

    def validate_voucher(self, code: str, customer_id: Optional[str] = None) -> Dict:
        """
        Valide un voucher avant de l'utiliser
        """
        try:
            url = f"{self.voucherify_base_url}/vouchers/{code}/validate"
            
            payload = {}
            if customer_id:
                payload["customer"] = {"source_id": customer_id}
            
            response = requests.post(
                url,
                headers=self._get_voucherify_headers(),
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "valid": data.get("valid", False),
                    "code": code,
                    "discount": self._extract_discount_info(data.get("voucher", {})),
                    "reason": data.get("reason", ""),
                    "applicable_to": data.get("applicable_to", {}),
                    "inapplicable_to": data.get("inapplicable_to", {})
                }
            else:
                return {
                    "valid": False,
                    "code": code,
                    "error": f"Validation failed: {response.status_code}"
                }
                
        except Exception as e:
            print(f"Error validating voucher: {e}")
            return {
                "valid": False,
                "code": code,
                "error": str(e)
            }

    def redeem_voucher(self, code: str, customer_id: str, order_amount: float) -> Dict:
        """
        Redeem (utiliser) un voucher
        """
        try:
            url = f"{self.voucherify_base_url}/vouchers/{code}/redemption"
            
            payload = {
                "customer": {
                    "source_id": customer_id
                },
                "order": {
                    "amount": int(order_amount * 100)  
                }
            }
            
            response = requests.post(
                url,
                headers=self._get_voucherify_headers(),
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "redemption_id": data.get("id"),
                    "code": code,
                    "discount_applied": self._extract_discount_info(data.get("voucher", {}))
                }
            else:
                return {
                    "success": False,
                    "error": f"Redemption failed: {response.status_code}",
                    "details": response.text
                }
                
        except Exception as e:
            print(f"Error redeeming voucher: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _search_promotions(self, query) -> List[Dict]:
        """
        Recherche de promotions via Google Shopping (réutilise BuyerAgent)
        """
        promotions = []
        
        try:
            results = self.buyer_agent.search(query, max_items=20)
            
            if results.get("error"):
                return promotions
            
            for product in results.get("results", []):
                price = product.get("price", 0)
                title = product.get("title", "")
                
                promo_keywords = ["sale", "discount", "deal", "off", "promo", "clearance"]
                
                if any(keyword in title.lower() for keyword in promo_keywords):
                    promotions.append({
                        "type": "promotion",
                        "source": "Google Shopping",
                        "product": product,
                        "discount_detected": True,
                        "title": title,
                        "price": price,
                        "url": product.get("url", ""),
                        "seller": product.get("source", "")
                    })
            
        except Exception as e:
            print(f"Error fetching promotions: {e}")
        
        return promotions

    def _detect_bundles(self, query) -> List[Dict]:
        """
        Détection de bundles (offres groupées)
        """
        bundles = []
        
        try:
            bundle_query = f"{query} bundle pack set"
            results = self.buyer_agent.search(bundle_query, max_items=10)
            
            if results.get("error"):
                return bundles
            
            for product in results.get("results", []):
                title = product.get("title", "").lower()
                
                if any(keyword in title for keyword in ["bundle", "pack", "set", "combo"]):
                    bundles.append({
                        "type": "bundle",
                        "source": "Google Shopping",
                        "product": product,
                        "title": product.get("title", ""),
                        "price": product.get("price", 0),
                        "url": product.get("url", ""),
                        "seller": product.get("source", "")
                    })
            
        except Exception as e:
            print(f"Error detecting bundles: {e}")
        
        return bundles

    def _process_deal(self, deal: Dict, user_id: str, query: str):
        """
        Traite un deal et décide s'il faut alerter
        """
        relevance_score = self._calculate_relevance(deal, user_id, query)
        
        deal["relevance_score"] = relevance_score
        deal["found_at"] = datetime.utcnow()
        deal["user_id"] = ObjectId(user_id)
        deal["query"] = query
        
        existing = self.deals_col.find_one({
            "user_id": ObjectId(user_id),
            "code": deal.get("code"),
            "name": deal.get("name")
        })
        
        if existing:
            print(f"Deal already exists, skipping...")
            return
        
        deal_id = self.deals_col.insert_one(deal).inserted_id
        
        print(f"Deal found: {deal.get('type')} - Score: {relevance_score:.2f}")
        
        if relevance_score >= self.IMMEDIATE_ALERT_THRESHOLD:
            self._send_immediate_alert(deal, user_id)
            
        elif relevance_score >= self.BUYER_NOTIFY_THRESHOLD:
            self._notify_buyer_agent(deal, user_id)

    def _calculate_relevance(self, deal: Dict, user_id: str, query: str) -> float:
        """
        Calcule un score de pertinence (0-1)
        """
        score = 0.0
        
        searchable_text = f"{deal.get('name', '')} {deal.get('title', '')} {deal.get('category', '')}".lower()
        query_words = query.lower().split()
        matches = sum(1 for word in query_words if word in searchable_text)
        query_match_score = matches / len(query_words) if query_words else 0
        score += query_match_score * 0.3
        
        discount_amount = deal.get("discount_amount", 0)
        discount_type = deal.get("discount_type", "")
        
        if discount_type == "PERCENT":
            discount_score = min(discount_amount / 100, 1.0)
        elif discount_type == "AMOUNT":
            discount_score = min(discount_amount / 50, 1.0)  
        else:
            discount_score = 0.5
        
        score += discount_score * 0.4
        
        user_prefs = self.user_agent.get_memory(user_id)
        likes = user_prefs.get("likes", [])
        
        pref_match = 0
        for like in likes:
            if like.lower() in searchable_text:
                pref_match = 1.0
                break
        
        score += pref_match * 0.2
        
        is_active = deal.get("active", False)
        has_expiration = bool(deal.get("expires") or deal.get("expiration_date"))
        
        validity_score = 0.5
        if is_active:
            validity_score += 0.3
        if has_expiration:
            validity_score += 0.2
        
        score += validity_score * 0.1
        
        return min(score, 1.0)

    def _send_immediate_alert(self, deal: Dict, user_id: str):
        """
        Envoie une alerte immédiate au UserAgent
        """
        alert = {
            "type": "HOT_DEAL",
            "priority": "HIGH",
            "deal_type": deal.get("type"),
            "source": deal.get("source", "Unknown"),
            "title": deal.get("name") or deal.get("title", "Deal trouvé!"),
            "code": deal.get("code", ""),
            "discount": deal.get("discount", "Promotion spéciale"),
            "description": deal.get("description", ""),
            "url": deal.get("url") or deal.get("redemption_url", ""),
            "expires": deal.get("expires") or deal.get("expiration_date", ""),
            "relevance_score": deal.get("relevance_score", 0),
            "timestamp": datetime.utcnow()
        }
        
        self.alerts_col.insert_one({
            **alert,
            "user_id": ObjectId(user_id),
            "sent": True
        })
        
        print(f"IMMEDIATE ALERT sent to user {user_id}")
        print(f"   → {alert['title']}")
        print(f"   → Code: {alert['code']}")
        print(f"   → Discount: {alert['discount']}")

    def _notify_buyer_agent(self, deal: Dict, user_id: str):
        """
        Notifie le BuyerAgent d'un deal intéressant
        """
        notification = {
            "type": "DEAL_OPPORTUNITY",
            "deal_type": deal.get("type"),
            "source": deal.get("source"),
            "code": deal.get("code", ""),
            "discount": deal.get("discount", ""),
            "product": deal.get("product", {}),
            "relevance_score": deal.get("relevance_score", 0),
            "timestamp": datetime.utcnow()
        }
        
        self.alerts_col.insert_one({
            **notification,
            "user_id": ObjectId(user_id),
            "sent_to": "buyer_agent"
        })
        
        print(f"BUYER NOTIFICATION sent")
        print(f"   → Deal type: {deal.get('type')}")
        print(f"   → Code: {deal.get('code', 'N/A')}")

    def get_active_deals(self, user_id: str, limit: int = 10) -> List[Dict]:
        """
        Récupère les deals actifs pour un utilisateur
        """
        deals = list(self.deals_col.find({
            "user_id": ObjectId(user_id),
            "relevance_score": {"$gte": self.BUYER_NOTIFY_THRESHOLD}
        }).sort("relevance_score", -1).limit(limit))
        
        for deal in deals:
            deal["_id"] = str(deal["_id"])
            deal["user_id"] = str(deal["user_id"])
            if "found_at" in deal:
                deal["found_at"] = deal["found_at"].isoformat()
        
        return deals

    def get_voucher_by_code(self, code: str) -> Optional[Dict]:
        """
        Récupère un voucher spécifique par son code
        """
        try:
            url = f"{self.voucherify_base_url}/vouchers/{code}"
            
            response = requests.get(
                url,
                headers=self._get_voucherify_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Voucher not found: {code}")
                return None
                
        except Exception as e:
            print(f"Error fetching voucher: {e}")
            return None

    def stop_monitoring(self, monitoring_id: str):
        """
        Arrête une surveillance active
        """
        self.deals_col.update_one(
            {"_id": ObjectId(monitoring_id)},
            {"$set": {"active": False}}
        )
        print(f"Monitoring stopped: {monitoring_id}")

    def find_deals_for_product(self, product: Dict) -> List[Dict]:
        """
        Cherche des coupons/deals pour un produit précis
        """
        deals = []
        
        product_name = product.get("title", "")
        vouchers = self._search_voucherify_vouchers(product_name)
        campaigns = self._search_voucherify_campaigns(product_name)
        promotions = self._search_promotions(product_name)
        bundles = self._detect_bundles(product_name)
        
        deals.extend(vouchers)
        deals.extend(campaigns)
        deals.extend(promotions)
        deals.extend(bundles)
    
        return deals
