# Secrets Management Guide

This document provides guidance on managing sensitive configuration and secrets for the Chat P1 Agent application.

## Table of Contents

- [Overview](#overview)
- [Development Environment](#development-environment)
- [Staging Environment](#staging-environment)
- [Production Environment](#production-environment)
- [Best Practices](#best-practices)
- [Secrets Rotation](#secrets-rotation)
- [Troubleshooting](#troubleshooting)

## Overview

The Chat P1 Agent requires several API keys and secrets to function:

### Required Secrets

1. **OpenAI API Key** - For LLM and embeddings
2. **Pinecone API Key** - For vector database
3. **Tavily API Key** - For real-time search
4. **Secret Key** - For session management (production only)

### Optional Secrets

1. **LangSmith API Key** - For tracing and monitoring
2. **Redis URL** - If using Redis for caching
3. **API Key** - If enabling API authentication

## Development Environment

### Local Development

For local development, use a `.env` file:

```bash
# Copy the example file
cp .env.example .env

# Edit with your actual API keys
nano .env
```

**Important**: Never commit `.env` files to version control!

### Getting API Keys

#### OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign up or log in
3. Navigate to API Keys section
4. Create a new secret key
5. Copy the key (you won't be able to see it again!)

#### Pinecone API Key

1. Go to [Pinecone Console](https://app.pinecone.io/)
2. Sign up or log in
3. Navigate to API Keys
4. Copy your API key
5. Note your environment (e.g., `us-east-1-aws`)

#### Tavily API Key

1. Go to [Tavily](https://tavily.com/)
2. Sign up for an account
3. Navigate to API Keys section
4. Copy your API key

#### LangSmith API Key (Optional)

1. Go to [LangSmith](https://smith.langchain.com/)
2. Sign up or log in
3. Navigate to Settings > API Keys
4. Create a new API key

### Generating Secret Key

For production deployments, generate a strong secret key:

```bash
# Using OpenSSL
openssl rand -hex 32

# Using Python
python -c "import secrets; print(secrets.token_hex(32))"
```

## Staging Environment

### Using Environment Variables

For staging deployments, use environment variables instead of files:

```bash
# Set environment variables
export OPENAI_API_KEY="sk-..."
export PINECONE_API_KEY="pcsk_..."
export TAVILY_API_KEY="tvly-..."
export SECRET_KEY="$(openssl rand -hex 32)"

# Start the application
docker-compose -f docker-compose.prod.yml up -d
```

### Docker Compose with Env File

```bash
# Create staging env file
cp .env.staging .env.staging.local

# Edit with actual keys
nano .env.staging.local

# Start with specific env file
docker-compose --env-file .env.staging.local up -d
```

## Production Environment

### Recommended Approaches

#### 1. Cloud Provider Secrets Manager

**AWS Secrets Manager**

```bash
# Store secrets
aws secretsmanager create-secret \
  --name chatp1/openai-api-key \
  --secret-string "sk-..."

# Retrieve in application startup script
export OPENAI_API_KEY=$(aws secretsmanager get-secret-value \
  --secret-id chatp1/openai-api-key \
  --query SecretString \
  --output text)
```

**Google Cloud Secret Manager**

```bash
# Store secrets
echo -n "sk-..." | gcloud secrets create openai-api-key --data-file=-

# Retrieve in application
export OPENAI_API_KEY=$(gcloud secrets versions access latest \
  --secret="openai-api-key")
```

**Azure Key Vault**

```bash
# Store secrets
az keyvault secret set \
  --vault-name chatp1-vault \
  --name openai-api-key \
  --value "sk-..."

# Retrieve in application
export OPENAI_API_KEY=$(az keyvault secret show \
  --vault-name chatp1-vault \
  --name openai-api-key \
  --query value -o tsv)
```

#### 2. Kubernetes Secrets

```yaml
# Create secret
apiVersion: v1
kind: Secret
metadata:
  name: chatp1-secrets
type: Opaque
stringData:
  openai-api-key: "sk-..."
  pinecone-api-key: "pcsk_..."
  tavily-api-key: "tvly-..."
  secret-key: "generated-secret-key"
```

```yaml
# Use in deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: chatp1-api
spec:
  template:
    spec:
      containers:
      - name: api
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: chatp1-secrets
              key: openai-api-key
```

#### 3. HashiCorp Vault

```bash
# Store secrets
vault kv put secret/chatp1 \
  openai_api_key="sk-..." \
  pinecone_api_key="pcsk_..." \
  tavily_api_key="tvly-..."

# Retrieve in application
vault kv get -field=openai_api_key secret/chatp1
```

#### 4. Docker Secrets (Docker Swarm)

```bash
# Create secrets
echo "sk-..." | docker secret create openai_api_key -
echo "pcsk_..." | docker secret create pinecone_api_key -

# Use in docker-compose
services:
  api:
    secrets:
      - openai_api_key
      - pinecone_api_key
    environment:
      - OPENAI_API_KEY_FILE=/run/secrets/openai_api_key

secrets:
  openai_api_key:
    external: true
  pinecone_api_key:
    external: true
```

### Environment Variables Only

For simpler deployments, use environment variables:

```bash
# In your deployment script or CI/CD pipeline
export OPENAI_API_KEY="${OPENAI_API_KEY}"
export PINECONE_API_KEY="${PINECONE_API_KEY}"
export TAVILY_API_KEY="${TAVILY_API_KEY}"
export SECRET_KEY="${SECRET_KEY}"

docker-compose -f docker-compose.prod.yml up -d
```

## Best Practices

### 1. Never Commit Secrets

```bash
# Add to .gitignore
.env
.env.*
!.env.example
!.env.development
!.env.staging
!.env.production
*.key
*.pem
secrets/
```

### 2. Use Different Keys Per Environment

- Development: Use free tier or test API keys
- Staging: Use separate keys from production
- Production: Use production-grade keys with appropriate limits

### 3. Rotate Secrets Regularly

- Rotate API keys every 90 days
- Rotate secret keys every 180 days
- Rotate immediately if compromised

### 4. Limit Secret Access

- Use principle of least privilege
- Only grant access to secrets that are needed
- Use IAM roles and policies to control access

### 5. Monitor Secret Usage

- Enable API key usage monitoring
- Set up alerts for unusual activity
- Track secret access in audit logs

### 6. Validate Configuration

Always validate configuration before deployment:

```bash
# Validate configuration
python scripts/validate_config.py --env production --strict

# Check for placeholder values
grep -r "your_.*_here" .env* && echo "Found placeholder values!"
```

## Secrets Rotation

### Rotating OpenAI API Key

1. Create new API key in OpenAI dashboard
2. Update secret in secrets manager
3. Restart application
4. Verify application is working
5. Delete old API key

### Rotating Pinecone API Key

1. Create new API key in Pinecone console
2. Update secret in secrets manager
3. Restart application
4. Verify vector store connectivity
5. Delete old API key

### Rotating Secret Key

1. Generate new secret key: `openssl rand -hex 32`
2. Update secret in secrets manager
3. Perform rolling restart to avoid session disruption
4. Monitor for any session-related issues

### Automated Rotation Script

```bash
#!/bin/bash
# rotate_secrets.sh

set -e

echo "Starting secret rotation..."

# Backup current secrets
kubectl get secret chatp1-secrets -o yaml > secrets-backup-$(date +%Y%m%d).yaml

# Update secrets (example for Kubernetes)
kubectl create secret generic chatp1-secrets-new \
  --from-literal=openai-api-key="${NEW_OPENAI_KEY}" \
  --from-literal=pinecone-api-key="${NEW_PINECONE_KEY}" \
  --from-literal=tavily-api-key="${NEW_TAVILY_KEY}" \
  --from-literal=secret-key="$(openssl rand -hex 32)" \
  --dry-run=client -o yaml | kubectl apply -f -

# Rolling restart
kubectl rollout restart deployment/chatp1-api
kubectl rollout restart deployment/chatp1-ui

# Wait for rollout
kubectl rollout status deployment/chatp1-api
kubectl rollout status deployment/chatp1-ui

echo "Secret rotation complete!"
```

## Troubleshooting

### Invalid API Key Errors

```bash
# Verify API key is set
echo $OPENAI_API_KEY | head -c 10

# Test API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Check application logs
docker-compose logs api | grep -i "api key"
```

### Secret Not Found

```bash
# Check if secret exists (Kubernetes)
kubectl get secrets

# Describe secret
kubectl describe secret chatp1-secrets

# Check environment variables in container
docker-compose exec api env | grep API_KEY
```

### Permission Denied

```bash
# Check IAM permissions (AWS)
aws sts get-caller-identity

# Check secret access
aws secretsmanager get-secret-value \
  --secret-id chatp1/openai-api-key
```

### Configuration Validation Failed

```bash
# Run validation with verbose output
python scripts/validate_config.py --env production

# Check for placeholder values
grep -E "(your_|_here)" .env.production

# Verify all required variables are set
python -c "
from dotenv import load_dotenv
import os
load_dotenv('.env.production')
required = ['OPENAI_API_KEY', 'PINECONE_API_KEY', 'TAVILY_API_KEY']
for var in required:
    print(f'{var}: {\"✓\" if os.getenv(var) else \"✗\"}'
)
"
```

## Additional Resources

- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Pinecone Documentation](https://docs.pinecone.io/)
- [Tavily API Documentation](https://docs.tavily.com/)
- [12-Factor App: Config](https://12factor.net/config)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
