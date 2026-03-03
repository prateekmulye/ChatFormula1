# Chat P1 UI Quick Start Guide

## Installation

```bash
# Install dependencies
poetry install

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
# Required: OPENAI_API_KEY, PINECONE_API_KEY, TAVILY_API_KEY
```

## Running the UI

```bash
# Option 1: Using Poetry script
poetry run f1-ui

# Option 2: Direct Streamlit command
poetry run streamlit run src/ui/app.py

# Option 3: From Python
poetry run python -c "from src.ui import main; main()"
```

The app will open in your browser at `http://localhost:8501`

## First Time Setup

1. **Configure API Keys**: Ensure `.env` has valid keys
2. **Initialize Vector Store**: Run data ingestion if needed
3. **Test Connection**: App will show status in sidebar
4. **Start Chatting**: Type a question in the input box

## Example Queries

Try these to test the system:

```
Who is leading the 2024 championship?
What happened in the last race?
Predict the winner of the next race
Tell me about Max Verstappen's career
What are the current technical regulations?
Compare Lewis Hamilton and Fernando Alonso
```

## Troubleshooting

### "Configuration Error" on startup
- Check `.env` file exists
- Verify all required API keys are set
- Ensure keys are valid (not placeholder values)

### "Failed to initialize agent"
- Check Pinecone index exists and is accessible
- Verify OpenAI API key has sufficient credits
- Test Tavily API key separately

### Slow responses
- First query may be slow (agent initialization)
- Check API rate limits
- Verify network connection
- Consider reducing `vector_search_top_k` in settings

### No sources displayed
- Vector store may be empty (run ingestion)
- Tavily search may have failed (check logs)
- Check metadata in agent response

## Development

### Project Structure
```
src/ui/
├── app.py           # Main Streamlit app
├── components.py    # Reusable UI components
├── __init__.py      # Module exports
├── README.md        # Full documentation
└── QUICK_START.md   # This file
```

### Key Files to Modify

**Customize appearance**: Edit `apply_custom_css()` in `app.py`

**Add new components**: Add functions to `components.py`

**Modify sidebar**: Edit `render_sidebar()` in `app.py`

**Change welcome message**: Edit `render_welcome_message()` in `components.py`

### Adding New Features

1. Add component function to `components.py`
2. Import in `app.py`
3. Call from appropriate render function
4. Test with `streamlit run`

### Debugging

Enable debug logging:
```python
# In .env
LOG_LEVEL=DEBUG
```

View logs in terminal where Streamlit is running.

## Configuration Options

### Environment Variables

```env
# Model Settings
OPENAI_MODEL=gpt-4-turbo          # or gpt-3.5-turbo
OPENAI_TEMPERATURE=0.7            # 0.0-2.0

# Search Settings
TAVILY_MAX_RESULTS=5              # 1-10
TAVILY_SEARCH_DEPTH=advanced      # basic or advanced

# RAG Settings
VECTOR_SEARCH_TOP_K=5             # 1-20
MAX_CONVERSATION_HISTORY=10       # 1-50
```

### UI Settings (in sidebar)

- **Temperature**: Controls response creativity
- **Conversation History**: Number of messages to remember
- **Theme**: Dark or light mode

## Tips

1. **Be Specific**: Mention years, drivers, or races for better context
2. **Follow Up**: Ask related questions naturally
3. **Use Feedback**: Thumbs up/down helps improve responses
4. **Clear When Needed**: Start fresh with "New Session"
5. **Check Sources**: Expand source sections to verify information

## Support

- **Documentation**: See `README.md` for full details
- **Issues**: Check logs for error messages
- **Configuration**: Verify `.env` settings
- **API Status**: Check provider status pages

## Next Steps

1. ✅ Run the UI and test basic queries
2. ✅ Explore different question types
3. ✅ Try the feedback buttons
4. ✅ Customize settings in sidebar
5. ✅ Review sources and metadata
6. ✅ Test error handling (invalid queries)
7. ✅ Try conversation continuity (follow-ups)

Enjoy using Chat P1! 🏎️
