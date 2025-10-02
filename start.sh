#!/bin/bash

echo "🎥 Starting LiveU Log Analyzer..."
echo ""
echo "Building and starting Docker containers..."
docker-compose up --build -d

echo ""
echo "⏳ Waiting for services to start..."
sleep 5

echo ""
echo "✅ Application is ready!"
echo ""
echo "🌐 Open your browser to:"
echo "   Frontend: http://localhost:3000"
echo "   Backend API: http://localhost:5000"
echo ""
echo "📊 To view logs:"
echo "   docker-compose logs -f"
echo ""
echo "🛑 To stop the application:"
echo "   docker-compose down"
echo ""
