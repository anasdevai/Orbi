#!/bin/bash

# BrowserAgent Build Script
# Creates a production-ready distribution package

set -e  # Exit on error

echo "🚀 Building BrowserAgent v3.0..."

# Create dist directory
echo "📁 Creating distribution directory..."
mkdir -p dist/BrowserAgent

# Copy extension files
echo "📦 Copying extension files..."
cp -r extension dist/BrowserAgent/

# Copy server files
echo "📦 Copying server files..."
cp -r server dist/BrowserAgent/

# Copy root files
echo "📦 Copying root files..."
cp requirements.txt dist/BrowserAgent/
cp run.py dist/BrowserAgent/
cp start.sh dist/BrowserAgent/
cp .env.example dist/BrowserAgent/
cp README.md dist/BrowserAgent/
cp PROJECT_CONSTITUTION.md dist/BrowserAgent/

# Clean up Python cache
echo "🧹 Cleaning up..."
find dist/BrowserAgent -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find dist/BrowserAgent -type f -name "*.pyc" -delete 2>/dev/null || true
find dist/BrowserAgent -type f -name ".DS_Store" -delete 2>/dev/null || true

# Remove any .env files (security)
rm -f dist/BrowserAgent/.env 2>/dev/null || true
rm -f dist/BrowserAgent/browseragent.db 2>/dev/null || true

# Create ZIP archive
echo "📦 Creating ZIP archive..."
cd dist
zip -r ../BrowserAgent-v3.0.zip BrowserAgent/ -q
cd ..

# Calculate size
SIZE=$(du -h BrowserAgent-v3.0.zip | cut -f1)

echo ""
echo "✅ Build complete!"
echo "📦 Package: BrowserAgent-v3.0.zip ($SIZE)"
echo ""
echo "📋 Installation instructions:"
echo "1. Extract the ZIP file"
echo "2. cd BrowserAgent"
echo "3. pip install -r requirements.txt"
echo "4. cp .env.example .env"
echo "5. Edit .env and add your OpenRouter API key"
echo "6. python server.py"
echo "7. Load extension/ folder in Chrome"
echo ""
echo "🎉 Ready to ship!"
