#!/bin/bash

# Setup script for GitHub Actions CI/CD
# This script helps you configure GitHub Secrets for automated deployment

set -e

echo "🚀 GitHub Actions CI/CD Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${YELLOW}⚠️  GitHub CLI (gh) is not installed${NC}"
    echo ""
    echo "To automatically set secrets, install GitHub CLI:"
    echo "  macOS: brew install gh"
    echo "  Linux: https://github.com/cli/cli/blob/trunk/docs/install_linux.md"
    echo "  Windows: https://github.com/cli/cli/releases"
    echo ""
    echo "Or manually add secrets at:"
    echo "  https://github.com/YOUR_USERNAME/YOUR_REPO/settings/secrets/actions"
    echo ""
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo -e "${YELLOW}⚠️  Not authenticated with GitHub${NC}"
    echo ""
    echo "Please authenticate first:"
    echo "  gh auth login"
    echo ""
    exit 1
fi

echo -e "${GREEN}✅ GitHub CLI is installed and authenticated${NC}"
echo ""

# Get repository info
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "")

if [ -z "$REPO" ]; then
    echo -e "${RED}❌ Not in a GitHub repository${NC}"
    echo ""
    echo "Please run this script from your repository root."
    exit 1
fi

echo -e "${BLUE}📦 Repository: $REPO${NC}"
echo ""

# Function to set secret
set_secret() {
    local name=$1
    local value=$2

    if [ -z "$value" ]; then
        echo -e "${YELLOW}⏭️  Skipping $name (empty value)${NC}"
        return
    fi

    echo "$value" | gh secret set "$name" --repo "$REPO"
    echo -e "${GREEN}✅ Set $name${NC}"
}

# Function to prompt for secret
prompt_secret() {
    local name=$1
    local description=$2
    local example=$3
    local required=$4

    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$name${NC}"
    echo "$description"
    if [ -n "$example" ]; then
        echo -e "${YELLOW}Example: $example${NC}"
    fi
    echo ""

    if [ "$required" = "true" ]; then
        echo -n "Enter value (required): "
    else
        echo -n "Enter value (optional, press Enter to skip): "
    fi

    read -r value

    if [ -n "$value" ]; then
        set_secret "$name" "$value"
    elif [ "$required" = "true" ]; then
        echo -e "${RED}❌ This secret is required!${NC}"
        exit 1
    else
        echo -e "${YELLOW}⏭️  Skipped${NC}"
    fi
}

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Required Secrets for Deployment${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Required secrets
prompt_secret \
    "RENDER_DEPLOY_HOOK_URL" \
    "Get from: Render Dashboard → Your Service → Settings → Deploy Hook" \
    "https://api.render.com/deploy/srv-xxxxx?key=xxxxx" \
    "true"

prompt_secret \
    "RENDER_URL" \
    "Your application URL on Render" \
    "https://f1-slipstream-ui.onrender.com" \
    "true"

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Optional Secrets (for advanced features)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

prompt_secret \
    "RENDER_SERVICE_ID" \
    "Your Render service ID (for advanced deployment features)" \
    "srv-xxxxx" \
    "false"

prompt_secret \
    "RENDER_API_KEY" \
    "Create at: https://dashboard.render.com/u/settings#api-keys" \
    "rnd_xxxxx" \
    "false"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Next steps:"
echo ""
echo "1. Verify secrets are set:"
echo "   gh secret list --repo $REPO"
echo ""
echo "2. Push a test commit:"
echo "   git commit -m 'Test CI workflow'"
echo "   git push origin main"
echo ""
echo "3. Deploy to Render:"
echo "   git commit -m 'deploy: Initial deployment'"
echo "   git push origin main"
echo ""
echo "4. Monitor workflows:"
echo "   https://github.com/$REPO/actions"
echo ""
echo "📖 Full documentation: docs/GITHUB_ACTIONS.md"
echo ""
