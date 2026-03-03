# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the Chat P1 Agent.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Configuration Issues](#configuration-issues)
- [API Connection Issues](#api-connection-issues)
- [Performance Issues](#performance-issues)
- [Docker Issues](#docker-issues)
- [Application Errors](#application-errors)
- [Data Ingestion Issues](#data-ingestion-issues)

## Quick Diagnostics

### Run Health Checks

```bash
# Check API health
curl http://localhost:8000/health

# Check UI health
curl http://localhost:8501/_stcore/health

# Check all services
make docker-health
```

### Validate Configuration

```bash
# Validate environment configuration
python scripts/validate_config.py

# Check for missing variables
python scripts/validate_config.py --strict

# Validate specific environment
python scripts/validate_config.py --env production
```

### Check Service Status

```bash
# Docker Compose
docker-compose ps

# View logs
docker-compose logs --tail=100

# Check resource usage
docker stats
```

## Configuration Issues

### Issue: Missing Environment Variables

**Error Message**:
```
ConfigurationError: Missing required variable: OPENAI_API_KEY
```

**Solution**:

```bash
# Check if .env file exists
ls -la .env

# If not, copy from example
cp .env.example .env

# Edit and add your API keys
nano .env

# Verify variables are set
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('OPENAI_API_KEY:', 'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET')"
```

### Issue: Invalid API Key Format

**Error Message**:
```
Warning: OPENAI_API_KEY doesn't start with expected prefix 'sk-'
```

**Solution**:

```bash
# Verify API key format
echo $OPENAI_API_KEY | head -c 10

# OpenAI keys should start with: sk-
# Pinecone keys should start with: pcsk_
# Tavily keys should start with: tvly-

# Get new keys if needed:
# OpenAI: https://platform.openai.com/api-keys
# Pinecone: https://app.pinecone.io/
# Tavily: https://tavily.com/
```

### Issue: Configuration Validation Failed

**Error Message**:
```
Invalid value for ENVIRONMENT: 'prod'. Valid values: development, staging, production
```

**Solution**:

```bash
# Check current value
grep ENVIRONMENT .env

# Fix the value
sed -i 's/ENVIRONMENT=prod/ENVIRONMENT=production/' .env

# Validate again
python scripts/validate_config.py
```

## API Connection Issues

### Issue: OpenAI API Connection Failed

**Error Message**:
```
OpenAI API error: Invalid API key provided
```

**Solution**:

```bash
# Test API key directly
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# If 401 Unauthorized:
# 1. Verify key is correct
# 2. Check if key is active in OpenAI dashboard
# 3. Ensure you have credits/billing set up

# If connection timeout:
# 1. Check internet connection
# 2. Check firewall rules
# 3. Try different network
```

### Issue: Pinecone Connection Failed

**Error Message**:
```
Failed to connect to Pinecone: Index 'f1-knowledge' not found
```

**Solution**:

```bash
# List available indexes
curl -X GET "https://api.pinecone.io/indexes" \
  -H "Api-Key: $PINECONE_API_KEY"

# Create index if it doesn't exist
# 1. Log into Pinecone console: https://app.pinecone.io/
# 2. Create new index with name matching PINECONE_INDEX_NAME
# 3. Set dimensions to 1536 (for text-embedding-3-small)
# 4. Choose metric: cosine

# Or use CLI (if available)
pinecone create-index f1-knowledge --dimension 1536 --metric cosine
```

### Issue: Tavily API Rate Limit

**Error Message**:
```
TavilyAPIError: Rate limit exceeded
```

**Solution**:

```bash
# Check your Tavily plan limits
# Log into: https://tavily.com/dashboard

# Reduce request frequency
# Edit .env:
TAVILY_MAX_RESULTS=3  # Reduce from 5

# Implement caching
CACHE_ENABLED=true
CACHE_TTL=3600

# Upgrade Tavily plan if needed
```

### Issue: LangSmith Connection Failed

**Error Message**:
```
Warning: Failed to connect to LangSmith
```

**Solution**:

```bash
# LangSmith is optional, you can disable it
LANGSMITH_TRACING=false

# Or verify API key
curl -X GET "https://api.smith.langchain.com/api/v1/sessions" \
  -H "x-api-key: $LANGSMITH_API_KEY"

# Get new key from: https://smith.langchain.com/
```

## Performance Issues

### Issue: Slow Response Times

**Symptoms**: Queries taking > 5 seconds to respond

**Diagnosis**:

```bash
# Check API logs for timing
docker-compose logs api | grep "duration"

# Check resource usage
docker stats

# Check network latency
ping api.openai.com
ping api.pinecone.io
```

**Solutions**:

```bash
# 1. Enable caching
CACHE_ENABLED=true
CACHE_TTL=3600

# 2. Reduce vector search results
PINECONE_TOP_K=3

# 3. Use faster OpenAI model
OPENAI_MODEL=gpt-3.5-turbo

# 4. Reduce max tokens
OPENAI_MAX_TOKENS=1000

# 5. Scale horizontally
docker-compose up -d --scale api=3
```

### Issue: High Memory Usage

**Symptoms**: Container using > 2GB RAM or getting OOM killed

**Diagnosis**:

```bash
# Check memory usage
docker stats

# Check for memory leaks
docker-compose logs api | grep -i "memory"
```

**Solutions**:

```bash
# 1. Increase memory limits
# Edit docker-compose.prod.yml:
deploy:
  resources:
    limits:
      memory: 4G

# 2. Reduce batch sizes
INGESTION_BATCH_SIZE=50
CHUNK_SIZE=500

# 3. Reduce conversation history
MAX_CONVERSATION_HISTORY=5

# 4. Restart services periodically
docker-compose restart api
```

### Issue: High CPU Usage

**Symptoms**: Container using > 80% CPU consistently

**Diagnosis**:

```bash
# Check CPU usage
docker stats

# Profile application
PROFILING_ENABLED=true
docker-compose restart api
```

**Solutions**:

```bash
# 1. Increase CPU limits
# Edit docker-compose.prod.yml:
deploy:
  resources:
    limits:
      cpus: '2'

# 2. Reduce concurrent requests
API_WORKERS=2

# 3. Optimize vector search
PINECONE_TOP_K=3

# 4. Use caching
CACHE_ENABLED=true
```

## Docker Issues

### Issue: Container Exits Immediately

**Symptoms**: Container starts then exits with code 1

**Diagnosis**:

```bash
# Check exit code
docker-compose ps

# View logs
docker-compose logs api

# Run container interactively
docker-compose run --rm api /bin/bash
```

**Common Causes**:

1. **Missing environment variables**
   ```bash
   python scripts/validate_config.py
   ```

2. **Port already in use**
   ```bash
   lsof -i :8000
   # Kill process or change port
   ```

3. **Invalid configuration**
   ```bash
   docker-compose config
   ```

### Issue: Cannot Connect to Container

**Symptoms**: `curl: (7) Failed to connect to localhost port 8000`

**Solutions**:

```bash
# 1. Check if container is running
docker-compose ps

# 2. Check port mapping
docker-compose port api 8000

# 3. Check if service is listening
docker-compose exec api netstat -tlnp | grep 8000

# 4. Check firewall
sudo ufw status
sudo ufw allow 8000

# 5. Try from inside container
docker-compose exec api curl localhost:8000/health
```

### Issue: Volume Permission Denied

**Symptoms**: `Permission denied` when accessing mounted volumes

**Solutions**:

```bash
# 1. Check volume ownership
ls -la data/

# 2. Fix permissions
sudo chown -R 1000:1000 data/

# 3. Or run as root (not recommended for production)
# Edit docker-compose.yml:
user: root
```

### Issue: Image Build Failed

**Symptoms**: `ERROR: failed to solve: process "/bin/sh -c ..."`

**Solutions**:

```bash
# 1. Clean build cache
docker-compose build --no-cache

# 2. Check Dockerfile syntax
docker-compose config

# 3. Check disk space
df -h

# 4. Clean up Docker
docker system prune -af
```

## Application Errors

### Issue: Import Error

**Error Message**:
```
ModuleNotFoundError: No module named 'langchain'
```

**Solution**:

```bash
# Rebuild container
docker-compose build --no-cache

# Or if using Poetry locally
poetry install
poetry shell
```

### Issue: Pydantic Validation Error

**Error Message**:
```
ValidationError: 1 validation error for Settings
```

**Solution**:

```bash
# Check configuration types
python scripts/validate_config.py

# Common issues:
# - String instead of integer
# - Invalid boolean value
# - Missing required field

# Fix in .env file
nano .env
```

### Issue: LangGraph State Error

**Error Message**:
```
StateError: Invalid state transition
```

**Solution**:

```bash
# Enable debug logging
LOG_LEVEL=DEBUG
docker-compose restart api

# Check logs for state transitions
docker-compose logs api | grep -i "state"

# Clear conversation state
# In UI: Click "New Conversation"
# Or restart services
docker-compose restart
```

### Issue: Streaming Response Failed

**Error Message**:
```
StreamingError: Connection closed while streaming
```

**Solution**:

```bash
# 1. Check network stability
ping api.openai.com

# 2. Increase timeout
API_TIMEOUT=60

# 3. Disable streaming temporarily
# In code, use non-streaming mode

# 4. Check proxy settings
unset HTTP_PROXY
unset HTTPS_PROXY
```

## Data Ingestion Issues

### Issue: Ingestion Failed

**Error Message**:
```
IngestionError: Failed to process documents
```

**Diagnosis**:

```bash
# Check ingestion logs
docker-compose logs api | grep -i "ingestion"

# Run ingestion manually
docker-compose run --rm api \
  python -m src.ingestion.cli ingest --source data/ --verbose
```

**Solutions**:

```bash
# 1. Check data format
# Ensure CSV/JSON files are valid

# 2. Reduce batch size
INGESTION_BATCH_SIZE=50

# 3. Check Pinecone quota
# Log into Pinecone console

# 4. Verify embeddings API
curl https://api.openai.com/v1/embeddings \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"input": "test", "model": "text-embedding-3-small"}'
```

### Issue: Duplicate Documents

**Symptoms**: Same documents appearing multiple times in search results

**Solution**:

```bash
# Clear and re-ingest
docker-compose run --rm api \
  python -m src.ingestion.cli clear --confirm

docker-compose run --rm api \
  python -m src.ingestion.cli ingest --source data/

# Or use incremental mode
docker-compose run --rm api \
  python -m src.ingestion.cli ingest --source data/ --incremental
```

### Issue: Embedding Generation Failed

**Error Message**:
```
EmbeddingError: Failed to generate embeddings
```

**Solution**:

```bash
# 1. Check OpenAI API status
curl https://status.openai.com/

# 2. Verify model availability
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# 3. Check rate limits
# Reduce batch size or add delays

# 4. Retry with exponential backoff
MAX_RETRIES=5
RETRY_BACKOFF_MULTIPLIER=2
```

## Getting More Help

### Enable Debug Logging

```bash
# Set debug level
LOG_LEVEL=DEBUG

# Restart services
docker-compose restart

# View detailed logs
docker-compose logs -f | tee debug.log
```

### Collect Diagnostic Information

```bash
# Create diagnostic report
cat > diagnostic_report.txt << EOF
=== System Information ===
$(uname -a)
$(docker --version)
$(docker-compose --version)

=== Service Status ===
$(docker-compose ps)

=== Recent Logs ===
$(docker-compose logs --tail=50)

=== Configuration ===
$(python scripts/validate_config.py)

=== Resource Usage ===
$(docker stats --no-stream)
EOF

# Share diagnostic_report.txt when seeking help
```

### Contact Support

If issues persist:

1. Check [GitHub Issues](https://github.com/your-repo/issues)
2. Review [Documentation](./README.md)
3. Join [Discord Community](https://discord.gg/your-server)
4. Email support: support@ChatP1.ai

Include:
- Error messages
- Diagnostic report
- Steps to reproduce
- Environment details
