# Chat P1 Streamlit UI

This module implements the Streamlit-based user interface for the Chat P1 chatbot.

## Features

### Main Application (`app.py`)
- **Session State Management**: Persistent conversation state across interactions
- **Agent Initialization**: Lazy loading of LangGraph agent and dependencies
- **Sidebar Controls**: Settings, conversation management, and system info
- **Theme Support**: Dark and light theme with custom CSS
- **Configuration**: Temperature control, history length, and model settings

### UI Components (`components.py`)
- **Message Display**: Role-based styling for user and assistant messages
- **Source Citations**: Expandable sections showing historical and current sources
- **Confidence Indicators**: Visual representation of prediction confidence
- **Feedback Mechanism**: Thumbs up/down buttons for user feedback
- **Error Handling**: User-friendly error messages with technical details
- **Loading States**: Progress indicators and typing animations
- **Welcome Message**: Helpful introduction for new users

## Usage

### Running the Application

```bash
# From the project root
poetry run streamlit run src/ui/app.py

# Or using the configured script
poetry run f1-ui
```

### Configuration

The UI requires the following environment variables (configured in `.env`):

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4-turbo
OPENAI_TEMPERATURE=0.7

# Pinecone Configuration
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=f1-knowledge

# Tavily Configuration
TAVILY_API_KEY=your_tavily_api_key
TAVILY_MAX_RESULTS=5
```

## Architecture

### Session State Structure

```python
st.session_state = {
    "session_id": str,              # Unique session identifier
    "messages": List[dict],         # Conversation history
    "agent_state": AgentState,      # Current agent state
    "settings": Settings,           # Application settings
    "agent_graph": F1AgentGraph,    # Compiled agent graph
    "vector_store": VectorStoreManager,
    "tavily_client": TavilyClient,
    "theme": str,                   # "dark" or "light"
    "feedback": dict,               # Message feedback tracking
    "last_error": Optional[str],    # Last error message
}
```

### Message Format

```python
{
    "role": "user" | "assistant",
    "content": str,                 # Message text (markdown supported)
    "metadata": {                   # Optional, for assistant messages
        "intent": str,
        "sources": List[dict],
        "confidence": float,
        "warnings": List[str],
    },
    "timestamp": datetime,
}
```

### Source Format

```python
{
    "type": "historical" | "current",
    "title": str,                   # Optional
    "url": str,                     # Optional
    "content": str,
    "score": float,                 # Relevance score (0-1)
    "metadata": dict,               # Additional metadata
}
```

## Components Reference

### Message Rendering

```python
render_message(
    role="assistant",
    content="Response text with **markdown**",
    metadata={
        "sources": [...],
        "confidence": 0.85,
    },
    message_id="unique_id",
)
```

### Source Citations

```python
render_sources([
    {
        "type": "historical",
        "content": "Historical context...",
        "score": 0.8,
    },
    {
        "type": "current",
        "title": "Latest F1 News",
        "url": "https://formula1.com/...",
        "content": "Current information...",
        "score": 0.9,
    },
])
```

### Confidence Display

```python
render_confidence(0.85)  # Shows "High Confidence (85%)"
```

### Feedback Buttons

```python
render_feedback_buttons("message_id_123")
```

### Error Messages

```python
render_error_message(
    error="Connection timeout",
    show_details=True,  # Show technical details in expander
)
```

## Customization

### Custom CSS

The `apply_custom_css()` function applies theme-specific styling. Modify the CSS in `app.py` to customize:

- Message bubble styling
- Source citation appearance
- Color schemes
- Spacing and layout

### Welcome Message

Customize the welcome message in `components.py` > `render_welcome_message()` to:

- Add/remove example queries
- Highlight specific features
- Include custom branding

### Sidebar Content

Modify `render_sidebar()` in `app.py` to:

- Add new settings controls
- Include additional metrics
- Customize help content

## Error Handling

The UI implements comprehensive error handling:

1. **Configuration Errors**: Caught during initialization, prevents app start
2. **Agent Initialization Errors**: Displayed with user-friendly message
3. **Query Processing Errors**: Caught and displayed per-message
4. **API Errors**: Mapped to user-friendly messages with fallback behavior

### Error Types

- `rate_limit`: API rate limit exceeded
- `api_key`: Invalid or missing API key
- `network`: Network connectivity issues
- `timeout`: Request timeout
- `vector_store`: Vector database unavailable
- `search`: Search service unavailable

## Performance Considerations

### Lazy Initialization

Components are initialized only when needed:
- Agent graph: First query
- Vector store: First query requiring historical data
- Tavily client: First query requiring real-time data

### Session State Optimization

- Message history limited by `max_conversation_history` setting
- Feedback stored per session, cleared on new session
- Agent state persisted for conversation continuity

### Streaming Support

The UI is designed to support streaming responses (future enhancement):
- Placeholder for streaming text
- Token-by-token display
- Interrupt capability

## Testing

### Manual Testing Checklist

- [ ] App launches without errors
- [ ] Welcome message displays correctly
- [ ] User can send messages
- [ ] Assistant responses appear
- [ ] Sources are expandable and readable
- [ ] Feedback buttons work
- [ ] Conversation can be cleared
- [ ] New session creates fresh state
- [ ] Settings persist across messages
- [ ] Errors display user-friendly messages
- [ ] Theme toggle works
- [ ] Sidebar metrics update

### Integration Testing

Test with actual agent:
```bash
# Ensure .env is configured
poetry run f1-ui
```

Test queries:
- "Who is leading the championship?"
- "What happened in the last race?"
- "Predict the winner of the next race"

## Troubleshooting

### "Configuration Error" on startup

- Check `.env` file exists and has all required variables
- Verify API keys are valid
- Check environment variable names match settings.py

### "Failed to initialize agent"

- Verify Pinecone index exists
- Check OpenAI API key is valid
- Ensure Tavily API key is valid
- Check network connectivity

### Messages not appearing

- Check browser console for errors
- Verify session state is initialized
- Check agent graph is compiled

### Slow responses

- Check API rate limits
- Verify vector store connection
- Monitor network latency
- Consider reducing `vector_search_top_k`

## Future Enhancements

- [ ] Streaming response display
- [ ] Voice input support
- [ ] Export conversation history
- [ ] Share conversation links
- [ ] Custom prompt templates
- [ ] Multi-language support
- [ ] Mobile-responsive design
- [ ] Keyboard shortcuts
- [ ] Search conversation history
- [ ] Conversation branching

## Dependencies

- `streamlit>=1.29.0`: UI framework
- `structlog>=23.3.0`: Structured logging
- `langchain>=0.1.0`: LLM framework
- `langgraph>=0.0.20`: Agent orchestration
- `pydantic>=2.5.3`: Data validation

See `pyproject.toml` for complete dependency list.
