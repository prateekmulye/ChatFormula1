# 🚀 GitHub Actions CI/CD Setup

Complete guide for setting up automated testing and deployment with GitHub Actions.

---

## Overview

This project uses GitHub Actions for:
- **Continuous Integration (CI)**: Code quality checks and tests on every push/PR
- **Continuous Deployment (CD)**: Automatic deployment to Render on `deploy:` commits

---

## Workflows

### 1. CI Workflow (`ci.yml`)

**Triggers**: Every push and pull request to `main` or `develop`

**Jobs**:
1. **Code Quality Checks**
   - Black formatting check
   - Ruff linting
   - mypy type checking

2. **Run Tests**
   - Unit tests with pytest
   - Coverage reporting
   - Upload to Codecov

3. **Build Docker Image**
   - Build and cache Docker image
   - Verify build succeeds

### 2. Deploy Workflow (`deploy.yml`)

**Triggers**: Push to `main` with commit message starting with `deploy:`

**Jobs**:
1. **Check Deploy**
   - Verify commit message starts with `deploy:`
   - Skip if not a deploy commit

2. **Deploy to Render**
   - Trigger Render deployment via webhook
   - Wait for deployment
   - Run health checks
   - Report deployment status

---

## Setup Instructions

### Step 1: Configure GitHub Secrets

Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions**

Add the following secrets:

#### Required for Deployment

1. **`RENDER_DEPLOY_HOOK_URL`**
   - Get from Render Dashboard → Your Service → Settings → Deploy Hook
   - Format: `https://api.render.com/deploy/srv-xxxxx?key=xxxxx`

2. **`RENDER_URL`**
   - Your application URL
   - Example: `https://chatp1-ui.onrender.com`

#### Optional (for full CI/CD)

3. **`RENDER_SERVICE_ID`**
   - Your Render service ID
   - Format: `srv-xxxxx`

4. **`RENDER_API_KEY`**
   - Create at: https://dashboard.render.com/u/settings#api-keys
   - Used for advanced deployment features

5. **`OPENAI_API_KEY`** (if running integration tests)
   - Your OpenAI API key
   - Only needed if tests make real API calls

6. **`PINECONE_API_KEY`** (if running integration tests)
   - Your Pinecone API key

7. **`TAVILY_API_KEY`** (if running integration tests)
   - Your Tavily API key

### Step 2: Get Render Deploy Hook

1. Go to Render Dashboard: https://dashboard.render.com
2. Select your service (e.g., `chatp1-ui`)
3. Go to **Settings** tab
4. Scroll to **Deploy Hook**
5. Click **Create Deploy Hook**
6. Copy the URL (looks like: `https://api.render.com/deploy/srv-xxxxx?key=xxxxx`)
7. Add to GitHub Secrets as `RENDER_DEPLOY_HOOK_URL`

### Step 3: Add Your Application URL

1. Copy your Render URL (e.g., `https://chatp1-ui.onrender.com`)
2. Add to GitHub Secrets as `RENDER_URL`

### Step 4: Enable GitHub Actions

1. Go to your repository → **Actions** tab
2. If prompted, click **"I understand my workflows, go ahead and enable them"**
3. Workflows will now run automatically

---

## Usage

### Running CI (Automatic)

CI runs automatically on every push and pull request:

```bash
# Push to main or develop
git push origin main

# Create a pull request
# CI will run automatically
```

**What happens**:
1. ✅ Code formatting checked
2. ✅ Linting performed
3. ✅ Type checking run
4. ✅ Tests executed
5. ✅ Docker image built

### Deploying to Render

To trigger a deployment, prefix your commit message with `deploy:`:

```bash
# Make your changes
git add .

# Commit with deploy: prefix
git commit -m "deploy: Add new feature for race predictions"

# Push to main
git push origin main
```

**What happens**:
1. ✅ CI runs (code quality + tests)
2. ✅ Docker image built
3. ✅ Deployment triggered on Render
4. ✅ Health checks performed
5. ✅ Deployment status reported

### Examples

```bash
# Deploy with feature description
git commit -m "deploy: Add caching for improved performance"

# Deploy with bug fix
git commit -m "deploy: Fix rate limiting issue"

# Deploy with version bump
git commit -m "deploy: Release v1.2.0"

# Regular commit (no deployment)
git commit -m "Update documentation"
git commit -m "Refactor agent code"
```

---

## Workflow Details

### CI Workflow

```yaml
Trigger: Push/PR to main or develop
├── Code Quality (runs in parallel)
│   ├── Black formatting check
│   ├── Ruff linting
│   └── mypy type checking
├── Tests (after code quality)
│   ├── Run pytest
│   ├── Generate coverage
│   └── Upload to Codecov
└── Build (after tests)
    └── Build Docker image
```

**Duration**: ~3-5 minutes

### Deploy Workflow

```yaml
Trigger: Push to main with "deploy:" prefix
├── Check Deploy
│   └── Verify commit message
└── Deploy (if deploy commit)
    ├── Trigger Render webhook
    ├── Wait for deployment
    ├── Run health checks
    └── Report status
```

**Duration**: ~5-10 minutes (includes Render build time)

---

## Monitoring Workflows

### View Workflow Runs

1. Go to your repository → **Actions** tab
2. See all workflow runs
3. Click on a run to see details
4. View logs for each job

### Check Deployment Status

After pushing a `deploy:` commit:

1. Go to **Actions** tab
2. Click on the latest workflow run
3. Watch the deployment progress
4. Check health check results

### Troubleshooting Failed Workflows

**Code Quality Failed**:
```bash
# Fix formatting
poetry run black src tests

# Fix linting issues
poetry run ruff check src tests --fix

# Check types
poetry run mypy src
```

**Tests Failed**:
```bash
# Run tests locally
poetry run pytest -v

# Run specific test
poetry run pytest tests/test_agent.py -v

# Check coverage
poetry run pytest --cov=src
```

**Deployment Failed**:
1. Check Render logs: https://dashboard.render.com
2. Verify environment variables are set
3. Check health endpoint: `https://your-app.onrender.com/health`
4. Review GitHub Actions logs

---

## Advanced Configuration

### Customize CI Workflow

Edit `.github/workflows/ci.yml`:

```yaml
# Change Python version
env:
  PYTHON_VERSION: "3.12"

# Add more test types
- name: Run integration tests
  run: poetry run pytest -m integration

# Add security scanning
- name: Security scan
  run: poetry run bandit -r src
```

### Customize Deploy Workflow

Edit `.github/workflows/deploy.yml`:

```yaml
# Change health check timeout
MAX_RETRIES=20  # Increase retries

# Add Slack notification
- name: Notify Slack
  uses: slackapi/slack-github-action@v1
  with:
    webhook-url: ${{ secrets.SLACK_WEBHOOK }}
```

### Add More Workflows

Create new workflow files in `.github/workflows/`:

**Example: Nightly Tests**
```yaml
# .github/workflows/nightly.yml
name: Nightly Tests
on:
  schedule:
    - cron: '0 0 * * *'  # Run at midnight daily
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      # ... test steps
```

---

## Best Practices

### Commit Messages

✅ **Good**:
```bash
git commit -m "deploy: Add vector search caching"
git commit -m "deploy: Fix rate limiter bug"
git commit -m "deploy: Release v1.2.0"
```

❌ **Bad**:
```bash
git commit -m "deploy"  # Too vague
git commit -m "Deploy: fix"  # Capital D won't trigger
git commit -m "deploy:fix"  # Missing space after colon
```

### Deployment Strategy

1. **Test locally first**
   ```bash
   poetry run pytest
   poetry run black src tests
   poetry run ruff check src tests
   ```

2. **Push to develop branch first**
   ```bash
   git push origin develop
   # Wait for CI to pass
   ```

3. **Merge to main and deploy**
   ```bash
   git checkout main
   git merge develop
   git commit -m "deploy: Merge feature X"
   git push origin main
   ```

### Monitoring

- Check GitHub Actions after every push
- Monitor Render dashboard during deployments
- Set up Slack/email notifications for failures
- Review logs regularly

---

## Troubleshooting

### "Workflow not running"

**Problem**: Pushed code but workflow didn't run

**Solutions**:
1. Check if Actions are enabled: Repository → Settings → Actions
2. Verify workflow file syntax: Use GitHub's workflow validator
3. Check branch name matches trigger: `main` or `develop`

### "Deploy workflow skipped"

**Problem**: Commit didn't trigger deployment

**Solutions**:
1. Verify commit message starts with `deploy:` (lowercase, with colon)
2. Check you pushed to `main` branch
3. View Actions tab to see skip reason

### "Deployment triggered but failed"

**Problem**: Deployment started but didn't complete

**Solutions**:
1. Check Render logs: Dashboard → Your Service → Logs
2. Verify environment variables are set in Render
3. Check health endpoint manually: `curl https://your-app.onrender.com/health`
4. Review GitHub Actions logs for error details

### "Tests failing in CI but pass locally"

**Problem**: Tests pass on your machine but fail in GitHub Actions

**Solutions**:
1. Check Python version matches: `.github/workflows/ci.yml`
2. Verify dependencies are locked: `poetry lock`
3. Check for environment-specific issues
4. Run tests in Docker locally: `docker-compose up --build`

---

## Cost Considerations

### GitHub Actions

- **Free tier**: 2,000 minutes/month for public repos
- **Private repos**: 2,000 minutes/month on free plan
- **Typical usage**: ~5 min per workflow run
- **Estimated runs**: ~400 runs/month on free tier

### Optimization Tips

1. **Cache dependencies**
   - Already configured in workflows
   - Reduces build time by ~50%

2. **Skip CI on docs changes**
   ```yaml
   on:
     push:
       paths-ignore:
         - '**.md'
         - 'docs/**'
   ```

3. **Use matrix builds sparingly**
   - Only test on one Python version
   - Add more versions only if needed

---

## Next Steps

1. ✅ Set up GitHub Secrets
2. ✅ Enable GitHub Actions
3. ✅ Push a test commit
4. ✅ Verify CI runs successfully
5. ✅ Try a deploy commit
6. ✅ Monitor deployment
7. ✅ Set up notifications (optional)

---

## Support

- **GitHub Actions Docs**: https://docs.github.com/en/actions
- **Render Docs**: https://render.com/docs
- **Workflow Issues**: Check Actions tab logs
- **Deployment Issues**: Check Render dashboard

---

**Happy deploying! 🚀**
