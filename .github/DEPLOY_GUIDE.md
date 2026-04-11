# 🚀 Quick Deploy Guide

## Deploy to Render with GitHub Actions

### One-Time Setup (5 minutes)

1. **Get Render Deploy Hook**
   ```
   Render Dashboard → Your Service → Settings → Deploy Hook → Create
   ```
   Copy the URL (looks like: `https://api.render.com/deploy/srv-xxxxx?key=xxxxx`)

2. **Add GitHub Secrets**
   ```
   GitHub Repo → Settings → Secrets and variables → Actions → New secret
   ```

   Add these secrets:
   - `RENDER_DEPLOY_HOOK_URL`: Your deploy hook URL
   - `RENDER_URL`: Your app URL (e.g., `https://f1-slipstream-ui.onrender.com`)

3. **Enable GitHub Actions**
   ```
   GitHub Repo → Actions → Enable workflows
   ```

### Deploy (30 seconds)

Prefix your commit message with `deploy:`:

```bash
# Make changes
git add .

# Commit with deploy: prefix
git commit -m "deploy: Add new feature"

# Push to main
git push origin main
```

That's it! GitHub Actions will:
1. ✅ Run code quality checks
2. ✅ Run tests
3. ✅ Build Docker image
4. ✅ Deploy to Render
5. ✅ Run health checks

### Monitor Deployment

Watch progress at: `https://github.com/YOUR_USERNAME/YOUR_REPO/actions`

### Examples

```bash
# Deploy new feature
git commit -m "deploy: Add caching for better performance"

# Deploy bug fix
git commit -m "deploy: Fix rate limiting issue"

# Deploy version
git commit -m "deploy: Release v1.2.0"

# Regular commit (no deploy)
git commit -m "Update documentation"
```

### Troubleshooting

**Deployment not triggered?**
- Check commit message starts with `deploy:` (lowercase)
- Verify you pushed to `main` branch
- Check Actions tab for skip reason

**Deployment failed?**
- Check Render logs: https://dashboard.render.com
- Review GitHub Actions logs
- Verify secrets are set correctly

### Full Documentation

See [docs/GITHUB_ACTIONS.md](../docs/GITHUB_ACTIONS.md) for complete guide.
