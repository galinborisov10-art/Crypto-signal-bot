#!/bin/bash
# Safe Git Push - Винаги pull преди push

echo "🔄 Checking for remote changes..."

# Pull latest changes first
git pull origin main

if [ $? -ne 0 ]; then
    echo "❌ Git pull failed! Fix conflicts first."
    exit 1
fi

echo "✅ Local code is up to date"

# Now push
echo "📤 Pushing changes..."
git push

if [ $? -eq 0 ]; then
    echo "✅ Push successful!"
else
    echo "❌ Push failed!"
    exit 1
fi
