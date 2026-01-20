# 🛒 Multi-Agent System for E-Commerce (SMA-Shopping)

![Status](https://img.shields.io/badge/Status-Prototype-blue)
![Python](https://img.shields.io/badge/Backend-FastAPI%20%7C%20CrewAI-green)
![React](https://img.shields.io/badge/Frontend-React%20%7C%20Vite-blueviolet)

This project is a prototype of a **Multi-Agent System (MAS)** designed to revolutionize the online shopping experience. Unlike traditional price comparison tools, this system acts as a true personal assistant capable of searching, recommending, finding hidden promotions, and even simulating a negotiation to get the best price.

---

## 🚀 Key Features

* **🕵️ Smart Search (Buyer Agent)**: Scrapes real-time data on Google Shopping via SerpAPI to find available products, their prices, and sellers.
* **🧠 Personalized Recommendation (Recommender Agent)**: Uses an LLM (GPT-4) to analyze products, understand nuances (price/quality ratio), and sort results based on the user's historical preferences.
* **💸 Deal Hunting (Deal Hunter Agent)**: Automatically checks for the existence of coupons or promo codes via the Voucherify API.
* **🤝 Social Negotiation (Negotiator Agent)**: Simulates an interaction between a virtual buyer and seller to attempt to negotiate the displayed price.
* **💾 Contextual Memory**: The system remembers the user's tastes (Likes/Dislikes) thanks to a MongoDB database.

---

## 🛠️ Technical Architecture

The project relies on a modern client-server architecture:

### Backend (API)
* **Language**: Python 3.10+
* **API Framework**: FastAPI (Asynchronous)
* **Agent Orchestration**: CrewAI
* **AI / LLM**: OpenAI API (GPT-4o-mini)
* **Database**: MongoDB Atlas

### Frontend (Interface)
* **Framework**: React.js + Vite
* **Styling**: TailwindCSS
* **Communication**: Asynchronous REST API calls

---

## 📦 Installation and Setup

Follow these steps to run the project locally.

### 1. Prerequisites
* Python 3.10 or higher
* Node.js and npm
* A MongoDB Atlas account (or local MongoDB)
* API Keys for: OpenAI, SerpAPI, Voucherify.

### 2. Clone the repository
```bash
git clone https://github.com/NourElhoda1/SMA.git
cd SMA
```

### 2. Server setup (Backend)
```bash
cd server
# Create a virtual environment (recommended)
python -m venv venv
# Activate the environment (Windows)
venv\Scripts\activate
# Activate the environment (Mac/Linux)
source venv/bin/activate

# Install packages
pip install -r requirements.txt

python main.py
# The server will start on http://localhost:8000
```

### 3. Client setup (Frontend)
```bash
cd client
npm install
npm run dev
```

## 🛠️ Technologies Used

### Backend (73.3%)
- **Python** - Main language for business logic
- Potential frameworks: Flask, Django, FastAPI
- AI/ML libraries for agent management

### Frontend (26.2%)
- **JavaScript** - Interactive user interface
- Potential frameworks: React, Vue.js, or Vanilla JS
- HTML/CSS for structure and design

## 📁 Project Structure

```
SMA/
├── client/
│   ├── src/              # Frontend source code
│   ├── public/           # Static files
│   ├── package.json      # npm dependencies
│   └── ...
├── server/
│   ├── agents/           # Agent modules
│   ├── models/           # Data models
│   ├── routes/           # API routes
│   ├── utils/            # Utilities
│   ├── main.py           # Entry point
│   └── requirements.txt  # Python dependencies
└── README.md
```

## 📊 Features

- ✨ Intelligent agent simulation
- 🔄 Inter-agent communication
- 📈 Real-time visualization
- 🎛️ Intuitive control interface
- 💾 Data persistence

---
