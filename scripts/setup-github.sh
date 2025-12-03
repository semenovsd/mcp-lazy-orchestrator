#!/bin/bash
# GitHub Repository Setup Script for Docker MCP Orchestrator
# Run this script after cloning or downloading the project

set -e

REPO_NAME="docker-mcp-orchestrator"
GITHUB_USER="semenovsd"

echo "=============================================="
echo "  Docker MCP Orchestrator - GitHub Setup"
echo "=============================================="
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "GitHub CLI (gh) not found."
    echo ""
    echo "Install it first:"
    echo "  Ubuntu: sudo apt install gh"
    echo "  macOS:  brew install gh"
    echo ""
    echo "Then authenticate: gh auth login"
    exit 1
fi

# Check authentication
if ! gh auth status &> /dev/null; then
    echo "Not authenticated with GitHub."
    echo "Run: gh auth login"
    exit 1
fi

echo "Creating GitHub repository..."

# Create repository
gh repo create "$REPO_NAME" \
    --public \
    --description "Reduce MCP token usage by 90%+ — Load Docker MCP servers on-demand instead of exposing all tools at once" \
    --homepage "https://github.com/$GITHUB_USER/$REPO_NAME" \
    --clone=false

echo "✓ Repository created: https://github.com/$GITHUB_USER/$REPO_NAME"
echo ""

# Initialize git if needed
if [ ! -d ".git" ]; then
    echo "Initializing git repository..."
    git init
fi

# Add remote
git remote remove origin 2>/dev/null || true
git remote add origin "https://github.com/$GITHUB_USER/$REPO_NAME.git"

# Add all files
echo "Adding files..."
git add .

# Commit
echo "Creating initial commit..."
git commit -m "Initial release v1.0.0

- Core orchestration tools for lazy-loading MCP servers
- Support for 8 Docker MCP Toolkit servers
- 90%+ token reduction compared to loading all tools
- English and Russian documentation
- Cursor and Claude Desktop configuration examples
- CC BY-NC 4.0 license"

# Push
echo "Pushing to GitHub..."
git branch -M main
git push -u origin main

echo ""
echo "=============================================="
echo "  ✅ Setup Complete!"
echo "=============================================="
echo ""
echo "Repository: https://github.com/$GITHUB_USER/$REPO_NAME"
echo ""
echo "Next steps:"
echo "1. Add topics: mcp, docker, cursor, claude, ai, token-optimization"
echo "2. Configure repository settings in GitHub"
echo "3. Share with the community!"
