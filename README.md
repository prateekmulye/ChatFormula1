# 🏎️ ChatFormula1

An AI-powered Formula 1 chatbot that provides real-time race information, predictions, and insights using advanced RAG (Retrieval-Augmented Generation) architecture.

## 🚀 Live Demo

**Try it now**: [https://chatformula1.com](https://chatformula1.com)

*Note: First load may take 30 seconds as the free tier wakes up.*

---

## 🗺️ Quick Navigation

- **New to the project?** → Start with [Setup Guide](docs/SETUP.md)
- **Want to deploy?** → Follow [Deployment Guide](docs/DEPLOYMENT.md)
- **Want to contribute?** → Read [Contributing Guide](docs/CONTRIBUTING.md)
- **Need help?** → Check [Troubleshooting](docs/TROUBLESHOOTING.md)
- **All documentation** → See [Documentation Index](docs/README.md)

---

## 📖 What It Does

ChatFormula1 is an intelligent chatbot that can:

- Answer questions about current F1 standings and race results
- Provide historical F1 statistics and records
- Generate race predictions based on data analysis
- Search for latest F1 news and updates
- Explain technical F1 concepts and regulations
- Maintain context across conversations

**Example Questions:**
- "Who won the 2023 F1 World Championship?"
- "What are the current driver standings?"
- "Predict the outcome of the next race"
- "Explain DRS in Formula 1"

---

## 🛠️ Tech Stack

### AI & Machine Learning
- **[LangChain](https://python.langchain.com/)** - Framework for building LLM applications
- **[LangGraph](https://langchain-ai.github.io/langgraph/)** - Library for building stateful, multi-actor applications with LLMs
- **[OpenAI GPT](https://platform.openai.com/)** - Large language model for generating responses
- **[OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)** - Text vectorization for semantic search

### Data & Search
- **[Pinecone](https://www.pinecone.io/)** - Vector database for semantic search and retrieval
- **[Tavily API](https://tavily.com/)** - Real-time web search API for current information

### Backend
- **[Python 3.11+](https://www.python.org/)** - Core programming language
- **[FastAPI](https://fastapi.tiangolo.com/)** - Modern web framework for building APIs
- **[Pydantic](https://docs.pydantic.dev/)** - Data validation using Python type hints
- **[Poetry](https://python-poetry.org/)** - Dependency management and packaging

### Frontend
- **[Streamlit](https://streamlit.io/)** - Framework for building interactive web applications

### Infrastructure
- **[Docker](https://www.docker.com/)** - Containerization platform
- **[Render](https://render.com/)** - Cloud hosting platform (free tier available)

### Observability - COMMING SOON
- **[Structlog](https://www.structlog.org/)** - Structured logging library
- **[Prometheus](https://prometheus.io/)** - Monitoring and alerting toolkit
- **[Grafana](https://grafana.com/)** - Analytics and monitoring platform

---

## 🏗️ Architecture

```
User Input
    ↓
Streamlit UI
    ↓
LangGraph Agent
    ├── Query Analysis
    ├── Routing (Vector Search / Web Search)
    ├── Context Ranking
    └── LLM Generation
    ↓
Response with Citations
```

**Key Components:**
- **RAG Pipeline**: Combines vector search with LLM generation for accurate, grounded responses
- **Multi-Source Integration**: Retrieves from both historical data (Pinecone) and real-time web (Tavily)
- **Intelligent Routing**: Automatically determines the best data source for each query
- **Rate Limiting**: Built-in protection to stay within free tier limits

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- [Poetry](https://python-poetry.org/docs/#installation) - Python dependency manager
- API Keys (all have free tiers):
  - [OpenAI API Key](https://platform.openai.com/api-keys)
  - [Pinecone API Key](https://app.pinecone.io/)
  - [Tavily API Key](https://app.tavily.com/)

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/chatformula1.git
   cd chatformula1
   ```

2. **Install dependencies**
   ```bash
   poetry install
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

4. **Run the application**
   ```bash
   # Option 1: Streamlit UI (recommended for testing)
   poetry run streamlit run src/ui/app.py
   
   # Option 2: FastAPI backend
   poetry run uvicorn src.api.main:app --reload
   ```

5. **Access the application**
   - Streamlit UI: http://localhost:8501
   - FastAPI docs: http://localhost:8000/docs

### Docker

```bash
# Build and run with Docker Compose
docker-compose up --build

# Access at:
# - UI: http://localhost:8501
# - API: http://localhost:8000
```

---

## 📚 Documentation

### Getting Started
- **[Setup Guide](docs/SETUP.md)** - Complete local development setup with troubleshooting
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Deploy to Render for free in 15 minutes
- **[Contributing Guide](docs/CONTRIBUTING.md)** - Guidelines for contributing to the project

### Technical Documentation
- **[Architecture Overview](docs/ARCHITECTURE.md)** - System design and component architecture
- **[API Reference](docs/API.md)** - REST API endpoints and usage
- **[Security Guide](docs/SECURITY.md)** - Security best practices and implementation
- **[Observability](docs/OBSERVABILITY.md)** - Monitoring, logging, and alerting setup
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions

**[📖 Full Documentation Index](docs/README.md)**

---

## 🎯 Deployment

### Automated with GitHub Actions

Deploy automatically on every commit prefixed with `deploy:`:

```bash
# One-time setup (5 minutes)
./scripts/setup_github_actions.sh

# Deploy with a single commit
git commit -m "deploy: Add new feature"
git push origin main
```

**What happens**: Code quality checks → Tests → Build → Deploy to Render → Health checks

📖 **Guide**: [GitHub Actions Quick Start](GITHUB_ACTIONS_QUICKSTART.md) | [Full Documentation](docs/GITHUB_ACTIONS.md)

## 📁 Project Structure

```
chatformula1/
├── src/                      # Source code
│   ├── agent/               # LangGraph agent implementation
│   ├── api/                 # FastAPI endpoints
│   ├── config/              # Configuration management
│   ├── ingestion/           # Data ingestion pipeline
│   ├── prompts/             # LLM prompt templates
│   ├── search/              # Tavily search integration
│   ├── tools/               # LangChain tools
│   ├── ui/                  # Streamlit interface
│   ├── utils/               # Utility functions
│   └── vector_store/        # Pinecone integration
├── tests/                   # Test suite
├── scripts/                 # Deployment and utility scripts
├── docs/                    # Documentation
│   ├── README.md           # Documentation index
│   ├── SETUP.md            # Local setup guide
│   ├── DEPLOYMENT.md       # Deployment guide
│   ├── CONTRIBUTING.md     # Contribution guidelines
│   ├── ARCHITECTURE.md     # System architecture
│   ├── API.md              # API reference
│   └── ...                 # Additional technical docs
├── pyproject.toml          # Poetry dependencies
├── Dockerfile              # Docker configuration
└── README.md               # This file (start here!)
```

---

## 🔒 Security & Rate Limiting

- API keys stored as environment variables (never committed)
- Input validation and sanitization
- Rate limiting: 3 requests/minute, 100 requests/day per user
- HTTPS encryption (automatic on Render)
- No storage of personally identifiable information (PII)

---

## 💰 Cost Optimization

The application is designed to run entirely on free tiers:

| Service | Free Tier | Usage Strategy |
|---------|-----------|----------------|
| Render | 750 hrs/month | Auto-sleep after 15min inactivity |
| OpenAI | $5 credit | Rate limited to 3 RPM, 200 RPD |
| Pinecone | 100K vectors | Efficient text chunking |
| Tavily | 1000/month | Limited to 30 searches/day |

---

## 🤝 Contributing

Contributions are welcome! Please see [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 📞 Contact

- **GitHub**: [Current Projects 🧠 🚧](https://github.com/prateekmulye)
- **LinkedIn**: [Say Hi! 🤝](https://www.linkedin.com/in/prateekmulye/)
- **Email**: prateek@chatformula1.com

---

**Built with ❤️ for Formula 1 fans and AI enthusiasts**
