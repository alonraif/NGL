#!/bin/bash

echo "🚀 Enabling Optimized Backend (v2.0)"
echo ""

# Backup original
if [ ! -f backend/app_original.py ]; then
    echo "📦 Backing up original app.py..."
    cp backend/app.py backend/app_original.py
fi

# Switch to optimized version
echo "⚡ Switching to optimized backend..."
cp backend/app_optimized.py backend/app.py
cp backend/process_optimizer.py backend/ 2>/dev/null || true

echo ""
echo "🔧 Rebuilding Docker containers..."
docker-compose down
docker-compose up --build -d

echo ""
echo "✅ Optimized backend enabled!"
echo ""
echo "📊 New Features:"
echo "  • Async processing (non-blocking)"
echo "  • Real-time progress updates"
echo "  • Result caching (1 hour)"
echo "  • 10-minute timeout (was 5)"
echo "  • Parallel decompression"
echo ""
echo "🌐 Access: http://localhost:3000"
echo ""
echo "📝 To revert to original:"
echo "  cp backend/app_original.py backend/app.py"
echo "  docker-compose up --build -d"
echo ""
