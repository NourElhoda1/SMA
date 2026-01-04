# 🛒 SMA Multi-Agent Shopping System - REFACTORED

> Advanced Multi-Agent System for intelligent product search, comparison, and personalized recommendations

## 🎯 What's New in This Version

### ✨ Major Improvements

1. **Fixed Agent Communication Pipeline**
   - Agents now properly pass data using CrewAI's `context` parameter
   - Sequential flow: Buyer → Comparator → Recommender
   - Each agent receives output from previous agent

2. **Intent Classification**
   - New classifier determines query type (Purchase/Preference/General)
   - Routes requests to appropriate agent pipeline
   - Reduces unnecessary API calls

3. **Robust Error Handling**
   - Try-catch blocks on all endpoints and agent methods
   - Graceful degradation when services fail
   - User-friendly error messages

4. **Advanced Features**
   - Price alert system
   - Budget constraint filtering
   - Preference extraction using dedicated LLM calls
   - Multi-site price comparison
   - Conversation history with intelligent context building

5. **API Rate Limiting**
   - Protects against abuse (10 requests/minute)
   - Prevents API quota exhaustion
   - Configurable limits

6. **Better Code Quality**
   - Type hints throughout
   - Comprehensive docstrings
   - Separated concerns (tools, agents, logic)
   - Modular architecture

---

## 🏗️ Architecture

```
User Query
    ↓
[Intent Classifier]
    ↓
    ├─→ PURCHASE → [Buyer Agent] → [Comparator Agent] → [Recommender Agent]
    ├─→ PREFERENCE → [Recommender Agent] (direct)
    └─→ GENERAL → [Recommender Agent] (direct)
    ↓
[Memory Update] → [Response to User]
```

### Agent Roles

| Agent | Role | Tools | Responsibility |
|-------|------|-------|----------------|
| **Intent Classifier** | Understands request type | OpenAI | Routes to correct pipeline |
| **Buyer Agent** | Product search | SerpAPI (Google Shopping) | Finds products with prices |
| **Comparator Agent** | Price analysis | OpenAI | Creates comparison tables |
| **Recommender Agent** | Final synthesis | OpenAI | Personalizes response |

---

## 🚀 Installation

### Prerequisites

- Python 3.9+
- MongoDB (running locally or cloud)
- OpenAI API key
- SerpAPI key

### Setup Steps

```bash
# 1. Clone repository
git clone <your-repo>
cd SMA

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 5. Start MongoDB (if local)
mongod --dbpath /path/to/data

# 6. Run server
cd server
uvicorn auth_service:app --reload --port 8000
```

---

## 🔑 Environment Variables

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `MONGO_URI` | MongoDB connection string | ✅ | `mongodb://localhost:27017/` |
| `JWT_SECRET` | Secret for JWT tokens | ✅ | `your-secret-key-here` |
| `OPENAI_API_KEY` | OpenAI API key | ✅ | `sk-...` |
| `SERPAPI_KEY` | SerpAPI key for product search | ✅ | `your-serpapi-key` |
| `ALLOWED_ORIGINS` | CORS allowed origins | ❌ | `http://localhost:5173` |

---

## 📡 API Endpoints

### Authentication

#### POST `/signup`
Create new user account
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "name": "John Doe"
}
```

#### POST `/token`
Login and get JWT token (OAuth2 form)
```
username: user@example.com
password: securepassword123
```

### User Profile

#### GET `/me`
Get current user profile with preferences
```json
{
  "email": "user@example.com",
  "name": "John Doe",
  "memory": {
    "likes": ["Sony", "wireless"],
    "dislikes": ["cheap brands"]
  },
  "active_alerts": 2
}
```

#### POST `/preferences`
Update user preferences
```json
{
  "likes": ["Nike", "Adidas", "running shoes"],
  "dislikes": ["leather", "expensive"]
}
```

### Chat

#### POST `/chat`
Send message to AI agents
```json
{
  "message": "Find me a good laptop under 1000€",
  "max_budget": 1000
}
```

**Response:**
```json
{
  "response": "## 📊 COMPARISON TABLE\n\n| Product | Price | ...\n\n🏆 BEST CHOICE: ..."
}
```

#### GET `/chat-history?limit=20`
Get conversation history

### Price Alerts

#### POST `/price-alerts`
Create price alert
```json
{
  "product_name": "iPhone 15 Pro",
  "target_price": 999.99,
  "product_url": "https://example.com/product"
}
```

#### GET `/price-alerts`
Get active price alerts

#### DELETE `/price-alerts/{alert_id}`
Delete price alert

---

## 🧪 Testing

### Manual Testing

```bash
# Test signup
curl -X POST http://localhost:8000/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123456"}'

# Test login
curl -X POST http://localhost:8000/token \
  -d "username=test@example.com&password=test123456"

# Test chat (replace TOKEN)
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"Find me wireless headphones under 100€","max_budget":100}'
```

### Automated Testing (Future)

```bash
pytest tests/
```

---

## 🔧 Configuration

### Rate Limiting

Adjust in `auth_service.py`:
```python
@limiter.limit("10/minute")  # Change to "20/minute", etc.
```

### Agent Verbosity

In `user_agent.py`:
```python
self.buyer_agent = Agent(
    verbose=True  # Set to False for less logging
)
```

### MongoDB Collections

- `users` - User accounts
- `user_memory` - User preferences (likes/dislikes)
- `chat_history` - Conversation history
- `price_alerts` - Price tracking alerts

---

## 📊 Database Schema

### Users Collection
```json
{
  "_id": ObjectId,
  "email": "user@example.com",
  "password_hash": "bcrypt_hash",
  "name": "John Doe",
  "created_at": ISODate
}
```

### User Memory Collection
```json
{
  "_id": ObjectId,
  "user_id": ObjectId,
  "likes": ["Sony", "wireless", "noise-cancelling"],
  "dislikes": ["cheap", "wired"],
  "updated_at": ISODate
}
```

### Chat History Collection
```json
{
  "_id": ObjectId,
  "user_id": ObjectId,
  "role": "user|assistant",
  "content": "Message text",
  "timestamp": ISODate
}
```

---

## 🎨 Example Usage

### Shopping Query
```
User: "I need wireless headphones under 150€, I like Sony and Bose"

System:
1. Classifies intent: PURCHASE
2. Buyer searches Google Shopping
3. Comparator creates table of 5 products
4. Recommender personalizes based on Sony/Bose preference
5. Returns comparison + recommendation
```

### Preference Query
```
User: "I really don't like cheap brands, I prefer quality"

System:
1. Classifies intent: PREFERENCE
2. Extracts: dislikes=["cheap brands"], likes=["quality"]
3. Updates memory
4. Recommender acknowledges preferences
```

---

## 🔐 Security Best Practices

- ✅ Passwords hashed with bcrypt
- ✅ JWT tokens for authentication
- ✅ Rate limiting to prevent abuse
- ✅ CORS configured
- ⚠️ Use HTTPS in production
- ⚠️ Rotate JWT_SECRET regularly
- ⚠️ Use strong passwords
- ⚠️ Monitor API usage

---

## 🚧 Known Limitations

1. **SerpAPI Quota** - Limited free tier (100 searches/month)
2. **No Async Operations** - API calls are synchronous (can be improved)
3. **No Caching** - Repeated searches hit APIs (add Redis caching)
4. **Basic Price Alerts** - No automatic checking (needs background worker)
5. **Limited Error Recovery** - Some edge cases may not be handled

---

## 🛣️ Roadmap

### Phase 1 (Current)
- [x] Multi-agent pipeline
- [x] Product search & comparison
- [x] User preferences
- [x] Price alerts API

### Phase 2 (Next)
- [ ] Async/await for all API calls
- [ ] Redis caching for search results
- [ ] Background worker for price alerts
- [ ] Web scraping for reviews
- [ ] Image search capability

### Phase 3 (Future)
- [ ] Multi-language support
- [ ] Voice interface
- [ ] Browser extension
- [ ] Mobile app
- [ ] Social sharing features

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

---

## 📝 License

This project is licensed under the MIT License.

---

## 🙏 Acknowledgments

- CrewAI for multi-agent framework
- OpenAI for GPT models
- SerpAPI for shopping data
- FastAPI community

---

## 📞 Support

For issues and questions:
- GitHub Issues: [Your repo]/issues
- Email: your-email@example.com
- Documentation: [Your docs link]

---

**Made with ❤️ for intelligent shopping**