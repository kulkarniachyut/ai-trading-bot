#!/bin/bash
# Pre-commit hook: runs before every commit
# Catches common mistakes before they land in the repo

set -e

echo "🔍 Running pre-commit checks..."

# 1. Check for secrets accidentally staged
echo "  Checking for leaked secrets..."
if git diff --cached --name-only | xargs grep -l "sk-ant-\|sk-proj-\|ghp_\|AKIA" 2>/dev/null; then
    echo "❌ BLOCKED: Potential API key found in staged files!"
    exit 1
fi

# 2. Check .env is not staged
if git diff --cached --name-only | grep -q "^\.env$"; then
    echo "❌ BLOCKED: .env file is staged! Remove it with: git reset HEAD .env"
    exit 1
fi

# 3. Check for print() statements (should use loguru)
PRINT_FILES=$(git diff --cached --name-only -- '*.py' | xargs grep -l "^\s*print(" 2>/dev/null || true)
if [ -n "$PRINT_FILES" ]; then
    echo "⚠️  WARNING: print() found in: $PRINT_FILES"
    echo "   Use loguru logger instead. Proceeding anyway..."
fi

# 4. Check for datetime.now() without timezone (should be timezone-aware)
TZ_FILES=$(git diff --cached --name-only -- '*.py' | xargs grep -l "datetime\.now()" 2>/dev/null || true)
if [ -n "$TZ_FILES" ]; then
    echo "⚠️  WARNING: datetime.now() without timezone in: $TZ_FILES"
    echo "   Use datetime.now(tz=ZoneInfo('Asia/Kolkata')) or UTC."
fi

# 5. Check for os.getenv (should use shared/utils/config.py)
ENV_FILES=$(git diff --cached --name-only -- '*.py' | xargs grep -l "os\.getenv\|os\.environ" 2>/dev/null || true)
if [ -n "$ENV_FILES" ]; then
    echo "⚠️  WARNING: Direct os.getenv() found in: $ENV_FILES"
    echo "   Use shared/utils/config.py instead."
fi

echo "✅ Pre-commit checks passed."
