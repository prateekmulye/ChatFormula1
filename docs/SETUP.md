# 🛠️ Setup Guide

Complete guide for setting up Chat P1 Agent locally.

---

## Prerequisites

### Required Software

1. **Python 3.11 or higher**
   - Download: https://www.python.org/downloads/
   - Verify: `python --version`

2. **Poetry** (Python dependency manager)
   - Install: https://python-poetry.org/docs/#installation
   - Quick install: `curl -sSL https://install.python-poetry.org | python3 -`
   - Verify: `poetry --version`

3. **Git**
   - Download: https://git-scm.com/downloads
   - Verify: `git --version`

### API Keys (All Free Tier Available)

1. **OpenAI API Key**
   - Sign up: https://platform.openai.com/
   - Get $5 free credit for new accounts
   - Create key: https://platform.openai.com/api-keys
   - Format: `sk-...`

2. **Pinecone API Key**
   - Sign up: https://www.pinecone.io/
   - Free tier: 100K vectors, 2M queries/month
   - Create key in dashboard
   - Format: `pcsk_...`

3. **Tavily API Key**
   - Sign up: https://tavily.com/
   - Free tier: 1000 searches/month
   - Create key in dashboard
   - Format: `tvly-...`

---

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/chatp1.git
cd chatp1
```

### 2. Install Dependencies

```bash
# Install all dependencies
poetry install

# Activate virtual environment
poetry shell
```

### 3. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your favorite editor
nano .env  # or vim, code, etc.
```

**Required Environment Variables:**

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Pinecone Configuration
PINECONE_API_KEY=pcsk-your-key-here
PINECONE_INDEX_NAME=f1-knowledge

# Tavily Configuration
TAVILY_API_KEY=tvly-your-key-here

# Application Configuration
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### 4. Verify Setup

```bash
# Run validation script
python scripts/validate_setup.py
```

This checks:
- Python version
- Dependencies installed
- Environment variables set
- API keys valid

---

## Running the Application

### Option 1: Streamlit UI (Recommended)

```bash
# Run Streamlit interface
poetry run streamlit run src/ui/app.py

# Or if in poetry shell:
streamlit run src/ui/app.py
```

Access at: **http://localhost:8501**

### Option 2: FastAPI Backend

```bash
# Run FastAPI server
poetry run uvicorn src.api.main:app --reload

# Or if in poetry shell:
uvicorn src.api.main:app --reload
```

Access at:
- API: **http://localhost:8000**
- Docs: **http://localhost:8000/docs**

### Option 3: Docker

```bash
# Build and run with Docker Compose
docker-compose up --build

# Run in background
docker-compose up -d

# Stop containers
docker-compose down
```

Access at:
- UI: **http://localhost:8501**
- API: **http://localhost:8000**

---

## Development

### Code Quality

```bash
# Format code with Black
poetry run black src tests

# Lint with Ruff
poetry run ruff check src tests

# Type check with mypy
poetry run mypy src
```

### Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src --cov-report=html

# Run specific test types
poetry run pytest -m unit        # Unit tests
poetry run pytest -m integration # Integration tests
poetry run pytest -m e2e         # End-to-end tests

# Run specific test file
poetry run pytest tests/test_agent.py
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
poetry run pre-commit install

# Run manually
poetry run pre-commit run --all-files
```

---

## Data Ingestion

### Setup Pinecone Index

```bash
# Create Pinecone index
python scripts/setup_production_pinecone.py
```

### Ingest F1 Data

```bash
# Ingest data from directory
poetry run f1-ingest --source data/f1_data/ --batch-size 50

# Or use the CLI directly
python -m src.ingestion.cli --source data/f1_data/
```

---

## Troubleshooting

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'src'`

**Solution**:
```bash
# Ensure you're in the project root
pwd

# Reinstall dependencies
poetry install

# Activate shell
poetry shell
```

### API Key Errors

**Problem**: `Invalid API key` or `Authentication failed`

**Solution**:
1. Check `.env` file exists
2. Verify API keys are correct (no extra spaces)
3. Ensure keys are not placeholder values
4. Check API key permissions in provider dashboard

### Port Already in Use

**Problem**: `Address already in use: 8501`

**Solution**:
```bash
# Find process using port
lsof -i :8501

# Kill process
kill -9 <PID>

# Or use different port
streamlit run src/ui/app.py --server.port 8502
```

### Docker Issues

**Problem**: Docker build fails or containers won't start

**Solution**:
```bash
# Clean Docker cache
docker-compose down -v
docker system prune -a

# Rebuild without cache
docker-compose build --no-cache
docker-compose up
```

### Pinecone Connection Errors

**Problem**: `Failed to connect to Pinecone`

**Solution**:
1. Verify API key is correct
2. Check index name matches
3. Ensure index is created (run setup script)
4. Check internet connection
5. Verify Pinecone service status

---

## Project Structure

```
chatp1/
├── src/                      # Source code
│   ├── agent/               # LangGraph agent
│   │   ├── graph.py        # Agent workflow
│   │   └── nodes.py        # Agent nodes
│   ├── api/                 # FastAPI endpoints
│   │   ├── main.py         # API entry point
│   │   └── routes/         # API routes
│   ├── config/              # Configuration
│   │   ├── settings.py     # Pydantic settings
│   │   └── logging.py      # Logging setup
│   ├── ingestion/           # Data ingestion
│   │   ├── cli.py          # CLI interface
│   │   └── pipeline.py     # Ingestion pipeline
│   ├── prompts/             # LLM prompts
│   ├── search/              # Tavily integration
│   ├── tools/               # LangChain tools
│   ├── ui/                  # Streamlit UI
│   │   └── app.py          # UI entry point
│   ├── utils/               # Utilities
│   └── vector_store/        # Pinecone integration
├── tests/                   # Tests
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   └── conftest.py         # Pytest fixtures
├── scripts/                 # Utility scripts
├── docs/                    # Documentation
├── monitoring/              # Monitoring configs
├── .env.example            # Environment template
├── pyproject.toml          # Poetry config
├── Dockerfile              # Docker config
└── docker-compose.yml      # Docker Compose config
```

---

## Next Steps

1. ✅ Complete setup and verify everything works
2. 📖 Read the [Deployment Guide](DEPLOYMENT.md) to deploy your own instance
3. 🤝 Check [Contributing Guide](CONTRIBUTING.md) to contribute
4. 🚀 Start building and experimenting!

---

## Getting Help

- Check the [main README](../README.md)
- Review [Deployment Guide](DEPLOYMENT.md)
- Open an issue on GitHub
- Check logs for detailed error messages

---

**Happy coding! 🏎️**
