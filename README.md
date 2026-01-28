# French Cloze SRS - Intelligent Language Learning System

A personal French learning application that combines spaced repetition, error analysis, and linguistic insights to create a reflective, meaning-driven learning experience.




**Core Principles:**
- Words are the unit of memory
- Mistakes are learning signals  
- Context variation builds fluency
- Intelligence over points

## ✨ Features

### 🧠 Smart Spaced Repetition
- Adaptive SRS algorithm (0-5 strength levels)
- Error-driven scheduling (mistakes resurface immediately)
- Verb-specific reinforcement drills
- Time-based decay modeling

### 📊 Session Intelligence
After each practice session, you get:
- **One-sentence headline**: "You stopped hesitating on *faire* — it's becoming automatic"
- **Strength analysis**: What improved (max 3 items)
- **Weakness diagnosis**: What's still unstable (max 2 items)  
- **Linguistic insight**: Why confusion happens + underlying grammar rule
- **Forward nudge**: What to focus on next

### 🔍 Error Classification
Automatically detects:
- Substitution errors (wrong word)
- Conjugation errors (wrong form)
- Spelling/typo errors

### 📚 Massive Content Library
- 100,000+ real French sentences from Tatoeba
- 380+ intelligently extracted high-frequency words
- Automatic lemmatization (matches all verb forms)
- English translations for context

### 🤖 Optional RAG Generation
- Falls back to AI-generated sentences when needed
- Uses semantic search to match difficulty level
- Contextually appropriate examples

## 🏗️ Architecture
```
Frontend (HTML/JS)
    ↓
FastAPI Backend
    ↓
PostgreSQL + pgvector
    ↓
Tatoeba Corpus (100k sentences)
```

### Tech Stack
- **Backend**: Python, FastAPI, SQLAlchemy
- **Database**: PostgreSQL 14+ with pgvector extension
- **NLP**: spaCy (French model)
- **AI** (optional): OpenAI GPT-4o-mini
- **Frontend**: Vanilla HTML/JavaScript

## 📦 Installation

### Prerequisites
- Python 3.10+
- PostgreSQL 14+
- ~1GB disk space

### 1. Clone & Setup
```bash
git clone <your-repo>
cd french-srs

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Install spaCy French Model
```bash
python -m spacy download fr_core_news_sm
```

### 3. Setup PostgreSQL
```bash
# Create database
psql -U postgres
CREATE DATABASE clozeclone OWNER your_username;
\c clozeclone
CREATE EXTENSION vector;
\q
```

### 4. Configure Environment
Create `.env` file:
```env
DATABASE_URL=postgresql://username:password@localhost:5432/clozeclone
OPENAI_API_KEY=your_key_here  # Optional, for RAG
```

### 5. Download Tatoeba Data
```bash
mkdir data
cd data
wget https://www.manythings.org/anki/fra-eng.zip
unzip fra-eng.zip
# This creates fra-eng.txt
```

### 6. Initialize Database
```bash
# Create tables
python -c "from app.core.database import Base, engine; Base.metadata.create_all(engine)"

# Extract vocabulary (5-10 minutes)
PYTHONPATH=. python scripts/extract_vocabulary_from_tatoeba.py

# Import sentences (~10 minutes for 100k sentences)
PYTHONPATH=. python scripts/import_tatoeba.py
```

### 7. Run the App
```bash
uvicorn app.main:app --reload
```

Visit: `http://localhost:8000`

## 📁 Project Structure
```
french-srs/
├── app/
│   ├── api/
│   │   └── questions.py          # Main API endpoints
│   ├── models/
│   │   ├── word.py               # Word vocabulary
│   │   ├── sentence.py           # Cloze sentences
│   │   ├── memory.py             # SRS state
│   │   └── session.py            # Session tracking
│   ├── services/
│   │   ├── srs.py                # Spaced repetition logic
│   │   ├── validator.py          # Answer validation
│   │   ├── error_classifier.py   # Error categorization
│   │   ├── session_analyzer.py   # Insight generation
│   │   └── rag_sentence_generator.py  # AI fallback
│   ├── core/
│   │   └── database.py           # DB connection
│   └── main.py                   # FastAPI app
├── scripts/
│   ├── extract_vocabulary_from_tatoeba.py  # NLP extraction
│   └── import_tatoeba.py                    # Sentence import
├── static/
│   └── index.html                # Frontend UI
├── data/
│   └── fra-eng.txt               # Tatoeba corpus
├── requirements.txt
├── .env
└── README.md
```

## 🗄️ Database Schema

### Core Tables
- **words** - Vocabulary (384 entries)
- **sentences** - Cloze tests (100k entries)
- **user_word_memory** - SRS state per word
- **session_attempts** - Individual answers
- **session_summaries** - Generated insights

### Key Relationships
```
words (1) ──── (many) sentences
words (1) ──── (1) user_word_memory
session_attempts (many) ──── (1) session_summaries
```

## 🎮 Usage

### Basic Practice Flow
1. Visit `http://localhost:8000`
2. See a French sentence with a blank: *"Je ___ à l'école"*
3. Type the missing word
4. Get immediate feedback
5. After 20 questions, see "What Changed Today?" summary

### Understanding the SRS
- **Strength 0-1**: Review in hours
- **Strength 2-3**: Review in days  
- **Strength 4-5**: Review in weeks
- Mistakes reset strength and trigger immediate review

### Session Insights
The system analyzes your session to show:
- Which patterns you're internalizing
- Why specific mistakes happen
- Linguistic explanations (not just "try harder")

## 🚀 Deployment

### Recommended: Railway
```bash
# Create Procfile
echo "web: uvicorn app.main:app --host 0.0.0.0 --port \$PORT" > Procfile

# Push to GitHub, connect to Railway
# Add PostgreSQL database in Railway dashboard
# Set DATABASE_URL environment variable
# Deploy!
```

**Note**: Vercel won't work (needs persistent database + long-running server).

Alternative platforms:
- **Render** (free tier)
- **DigitalOcean App Platform** ($5/month)
- **Heroku** (paid only now)

## 💰 Cost Breakdown

### Free Tier (No RAG)
- Railway: $0-5/month
- Storage: ~50MB (sentences only)
- **Total: $0-5/month**

### With RAG Enabled
- OpenAI embeddings: $0.0001 per sentence
- Generate on-demand: ~$1-2/month typical usage
- **Total: $5-10/month**

## 🔧 Configuration

### Disable RAG (Recommended)
In `app/api/questions.py`, replace RAG block with:
```python
if not sentences:
    print(f"⚠️ No sentences for '{word.text}', skipping...")
    return get_next_question(db)
```

### Adjust SRS Intervals
Edit `app/services/srs.py`:
```python
INTERVALS = {
    0: timedelta(minutes=5),
    1: timedelta(hours=4),
    # ... customize these
}
```

### Change Session Length
In `static/index.html`:
```javascript
if (questionCount >= 20) {  // Change this number
    showSessionSummary();
}
```

## 🐛 Troubleshooting

### "No words due for review"
```sql
-- Reset all review dates to now
UPDATE user_word_memory SET next_review_at = NOW() - INTERVAL '1 hour';
```

### "Relation 'sentences' does not exist"
```bash
python -c "from app.core.database import Base, engine; Base.metadata.create_all(engine)"
```

### Import script finds 0 words
Your vocabulary wasn't extracted. Run:
```bash
PYTHONPATH=. python scripts/extract_vocabulary_from_tatoeba.py
```

### pgvector errors
```sql
-- Enable extension
psql -U your_user -d clozeclone
CREATE EXTENSION vector;
```

## 📈 Future Enhancements

### Planned
- [ ] Tense-specific strength tracking
- [ ] Grammar pattern recognition
- [ ] CEFR level progression
- [ ] Export session history
- [ ] Streak tracking (non-gamified)

### Not Planned
- ❌ Multiple users (single-user design)
- ❌ Mobile app (web-first)
- ❌ Social features
- ❌ Leaderboards/badges

## 🤝 Contributing

This is a personal learning project, but if you find it useful:
- Fork and adapt for your language
- Share interesting insights you discover
- Report bugs via issues

## 📝 License

MIT License 

## 🙏 Acknowledgments

- **Tatoeba Project** - 100k+ sentence pairs
- **spaCy** - French NLP
- **Clozemaster** - Inspiration for cloze-based learning
- **ChatGPT** - Architecture consultation

## 📚 Learning Resources

- [Tatoeba Downloads](https://tatoeba.org/en/downloads)
- [spaCy French Model](https://spacy.io/models/fr)
- [French Grammar Reference](https://www.lawlessfrench.com/)

---

**Built with 🧠 for learners who want to understand, not just memorize.**
