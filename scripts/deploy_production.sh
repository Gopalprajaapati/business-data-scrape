#!/bin/bash
# scripts/deploy_production.sh

set -e

echo "🚀 Starting Production Deployment..."

# Load environment
source .env.production

# Validation checks
echo "🔍 Running pre-deployment checks..."
python scripts/production_checklist.py

# Maintenance mode
echo "🛠️  Enabling maintenance mode..."
curl -X POST -H "Content-Type: application/json" -d '{"maintenance": true}' http://localhost:5000/api/admin/maintenance

# Backup database
echo "💾 Creating database backup..."
docker-compose exec db pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup_$(date +%Y%m%d_%H%M%S).sql

# Pull latest changes
echo "📥 Pulling latest code..."
git pull origin main

# Build and deploy
echo "🐳 Building and deploying containers..."
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Wait for services
echo "⏳ Waiting for services to start..."
sleep 30

# Run migrations
echo "🗃️  Running database migrations..."
docker-compose exec web flask db upgrade

# Run tests
echo "🧪 Running production tests..."
docker-compose exec web python -m pytest tests/ -v

# Warm up cache
echo "🔥 Warming up cache..."
curl -s http://localhost:5000/health > /dev/null
curl -s http://localhost:5000/api/analytics/dashboard > /dev/null

# Disable maintenance mode
echo "🎉 Disabling maintenance mode..."
curl -X POST -H "Content-Type: application/json" -d '{"maintenance": false}' http://localhost:5000/api/admin/maintenance

# Health check
echo "❤️  Final health check..."
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/health)
if [ $response -eq 200 ]; then
    echo "✅ Deployment completed successfully!"
else
    echo "❌ Deployment failed - health check returned $response"
    exit 1
fi

# Notify success
echo "📢 Deployment completed at $(date)"