# Money Tracker (Finance-Tracker)

An intelligent, AI-powered personal finance management application designed to automate transaction categorization, detect anomalies, and provide deep insights into your spending habits. 

Money Tracker combines a robust Python FastAPI backend with a sleek, interactive React frontend, utilizing advanced LLM integrations to parse bank statements and dynamically categorize expenses.

## 🚀 Features

### Core
- **Automated Statement Ingestion**: Upload PDF or CSV bank statements. The system automatically parses and extracts transaction data.
- **AI-Powered Categorization**: Uses LLMs (Gemini / Qwen) and a semantic dictionary to understand merchants and map them to standard categories (e.g., Food, Travel, Rent).
- **Interactive Review Queue**: Unsure transactions are flagged for manual review, allowing you to train the system with permanent rules.

### Analytics & Insights
- **Dashboard**: Visual breakdowns of spending via interactive charts (Recharts).
- **Anomaly Detection**: Statistically identifies unusual spending based on your historical patterns.
- **Recurring Charge Detection**: Automatically finds subscriptions and recurring bills.
- **Budget Tracking**: Compare actual spending against monthly budgets.

### UI / UX
- **Beautiful, Modern Interface**: Dark-themed, glassmorphic UI built with React and Vite.
- **Custom Vector Assets**: Uses custom hand-drawn SVG face icons (Koboyo style) for categories, ensuring a fun, personal touch while maintaining strict accessibility standards.

## 🛠️ Tech Stack

### Frontend
- **Framework**: React 18, Vite, TypeScript
- **Styling**: Modern CSS (Glassmorphism, Dark Theme)
- **Icons**: Lucide React + Custom Hand-Drawn SVGs
- **Charts**: Recharts

### Backend
- **Framework**: FastAPI (Python 3.12+)
- **Database**: SQLite (SQLAlchemy ORM)
- **AI/LLM**: Integrations with Gemini and Qwen for semantic parsing
- **Data Parsing**: PyPDF for secure PDF extraction

## 📦 Project Structure

```
├── Backend/               # FastAPI server, LLM gateway, DB models, and services
│   ├── app/api/           # REST endpoints
│   ├── app/src/           # Core logic (categoriser, insights, parsers)
│   └── main.py            # Entry point
├── frontend/              # React Vite application
│   ├── src/pages/         # Dashboards, Transactions, Review, etc.
│   └── src/components/    # Reusable UI components (CustomFaces, etc.)
├── Specs/                 # Detailed High-Level and Low-Level Design documents
└── .agents/               # Custom AI agent skills (UI/UX Pro Max, Design)
```

## 🚀 Getting Started

### 1. Backend Setup
```bash
cd Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start the server
fastapi dev main.py
```

### 2. Frontend Setup
```bash
cd frontend
npm install

# Start the dev server
npm run dev
```

### 3. Environment Variables
Copy the `.env.example` file in the `Backend/` directory to `.env` and add your API keys (e.g., OpenAI, Gemini).

## 🔒 Security
- This repository uses a highly configured `.gitignore` to ensure that API keys, `.env` files, virtual environments, and SQLite databases are never committed to version control.