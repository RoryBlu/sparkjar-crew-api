# Railway Deployment Guide for Chat with Memory v1

## Prerequisites

1. Railway account with project created
2. Environment variables configured in Railway
3. Redis and PostgreSQL services provisioned

## Environment Variables

Configure these in your Railway project settings:

```bash
# Core Services
DATABASE_URL=postgresql://user:pass@host:5432/dbname
REDIS_URL=redis://user:pass@host:6379
MEMORY_INTERNAL_API_URL=http://memory-internal.railway.internal:8001
MCP_REGISTRY_URL=http://mcp-registry.railway.internal:8000
CHROMA_URL=http://chroma.railway.internal:8000

# Authentication
API_SECRET_KEY=your-secret-key-here
MCP_REGISTRY_AUTH_TOKEN=your-mcp-token

# Chat Configuration
CHAT_SESSION_TTL_HOURS=24
CHAT_RATE_LIMIT_PER_MINUTE=20
CHAT_RATE_LIMIT_PER_HOUR=200
CHAT_MAX_MESSAGE_LENGTH=10240

# OpenAI (for LLM)
OPENAI_API_KEY=sk-your-openai-key

# Monitoring
LOG_LEVEL=INFO
SENTRY_DSN=https://your-sentry-dsn  # Optional
```

## Deployment Steps

### 1. Initial Setup

```bash
# Clone the repository
git clone https://github.com/sparkjar/crew-api.git
cd crew-api

# Create Railway project
railway login
railway link

# Create services
railway service create chat-api
railway service create redis
railway service create postgres
```

### 2. Configure Services

#### Redis Service
```bash
# Set Redis environment
railway env set REDIS_URL=${{REDIS.REDIS_URL}} -s chat-api
```

#### PostgreSQL Service
```bash
# Set database URL
railway env set DATABASE_URL=${{POSTGRES.DATABASE_URL}} -s chat-api

# Run migrations
railway run python scripts/migrate_database.py
```

### 3. Deploy Chat Service

```bash
# Deploy to Railway
railway up

# Or use GitHub integration
# Connect your GitHub repo in Railway dashboard
```

### 4. Health Checks

Railway will automatically check the `/health` endpoint. Ensure it returns:

```json
{
  "status": "healthy",
  "services": {
    "redis": "connected",
    "database": "connected",
    "memory_service": "connected"
  }
}
```

### 5. Post-Deployment

```bash
# Check logs
railway logs -s chat-api

# Run deployment validation
railway run python scripts/validate_deployment.py

# Test the API
curl -X GET https://your-app.railway.app/health
```

## Service Configuration

### Chat API Service

```yaml
# railway.yml (alternative to railway.json)
services:
  chat-api:
    build:
      builder: NIXPACKS
      buildCommand: pip install -r requirements.txt
    deploy:
      startCommand: uvicorn src.chat.api.main:app --host 0.0.0.0 --port $PORT
      healthcheckPath: /health
      healthcheckTimeout: 30
      numReplicas: 1
      restartPolicyType: ON_FAILURE
      restartPolicyMaxRetries: 3
    envs:
      PYTHON_VERSION: "3.11"
      PORT: 8000
```

### Resource Limits

For single-developer deployment:

```yaml
services:
  chat-api:
    deploy:
      numReplicas: 1
      resources:
        limits:
          memory: 512Mi
          cpu: 500m
```

## Monitoring Setup

### 1. Railway Metrics

Railway provides built-in metrics:
- CPU usage
- Memory usage
- Network I/O
- Request count

Access via Railway dashboard → Metrics tab

### 2. Application Logs

```python
# Configure structured logging
import structlog

logger = structlog.get_logger()

# Log important events
logger.info("chat_request", 
    session_id=session_id,
    mode=mode,
    memory_count=len(memories)
)
```

### 3. Health Endpoint

The `/health` endpoint provides:
- Service connectivity
- Response times
- Error rates

```bash
# Monitor health
watch -n 30 'curl -s https://your-app.railway.app/health | jq'
```

## Troubleshooting

### Common Issues

1. **Memory Service Connection Failed**
   ```bash
   # Check internal networking
   railway run ping memory-internal.railway.internal
   
   # Verify environment variable
   railway variables -s chat-api | grep MEMORY_INTERNAL_API_URL
   ```

2. **Redis Connection Issues**
   ```bash
   # Test Redis connection
   railway run python -c "import redis; r = redis.from_url('$REDIS_URL'); print(r.ping())"
   ```

3. **High Memory Usage**
   ```bash
   # Check for memory leaks
   railway logs -s chat-api | grep "memory"
   
   # Restart service
   railway restart -s chat-api
   ```

4. **Slow Response Times**
   - Check memory service response times
   - Verify Redis is not full
   - Review database query performance

### Debug Mode

Enable debug logging:

```bash
railway env set LOG_LEVEL=DEBUG -s chat-api
railway restart -s chat-api
```

## Rollback Procedure

If deployment fails:

1. **Immediate Rollback**
   ```bash
   # Railway automatically keeps previous deployments
   # Go to Railway dashboard → Deployments → Rollback
   ```

2. **Manual Rollback**
   ```bash
   # Deploy specific commit
   git checkout <previous-commit>
   railway up
   ```

3. **Database Rollback**
   ```bash
   # If migrations were run
   railway run python scripts/rollback_migration.py
   ```

## Performance Optimization

### 1. Redis Configuration

```bash
# Set Redis memory policy
railway env set REDIS_MAXMEMORY_POLICY=allkeys-lru -s redis
```

### 2. Connection Pooling

Already configured in the application:
- Database: 5 connections
- Redis: 10 connections
- Memory Service: 20 connections

### 3. Caching Headers

The API sets appropriate cache headers:
- Static responses: 5 minutes
- Dynamic responses: No cache
- Memory search results: 1 minute

## Security Checklist

- [ ] All environment variables set
- [ ] HTTPS enabled (automatic on Railway)
- [ ] Rate limiting configured
- [ ] Authentication tokens rotated
- [ ] Database backups enabled
- [ ] Logging does not contain sensitive data

## Scaling Considerations

When ready to scale:

1. **Increase Replicas**
   ```bash
   railway env set RAILWAY_REPLICA_COUNT=2 -s chat-api
   ```

2. **Add Redis Clustering**
   - Upgrade to Redis cluster
   - Update connection string

3. **Database Read Replicas**
   - Add read replicas for memory queries
   - Update connection pooling

## Maintenance

### Regular Tasks

1. **Weekly**
   - Review error logs
   - Check memory usage trends
   - Update dependencies

2. **Monthly**
   - Rotate API keys
   - Review security events
   - Performance analysis

3. **Quarterly**
   - Full security audit
   - Dependency updates
   - Capacity planning

### Backup Strategy

Railway provides automatic backups for databases. Additionally:

```bash
# Manual backup
railway run python scripts/backup_sessions.py

# Export learning reports
railway run python scripts/export_learning_data.py
```