# Troubleshooting Guide

Common issues and solutions for Astrovox AI.

## Installation Issues

### npm install fails

**Symptoms**: `npm install` exits with errors

**Solutions**:
- Clear cache: `npm cache clean --force`
- Delete `node_modules` and `package-lock.json`, then reinstall
- Ensure Node.js 18+ is installed
- Check for peer dependency conflicts: `npm install --legacy-peer-deps`

### Python dependencies fail

**Symptoms**: `pip install` errors on Windows

**Solutions**:
- Upgrade pip: `python -m pip install --upgrade pip`
- Use virtual environment: `python -m venv venv`
- On Windows, ensure Visual C++ Build Tools installed

## Runtime Issues

### Backend won't start

**Symptoms**: `uvicorn` fails to start

**Solutions**:
- Check port 8000 is available: `netstat -ano | findstr :8000`
- Verify `.env` file exists and has required variables
- Check database connectivity: `psql $DATABASE_URL`
- Review logs for specific error messages

### Frontend won't start

**Symptoms**: `npm run dev` fails

**Solutions**:
- Ensure port 5173 is available
- Delete `.vite` cache directory
- Check for TypeScript errors: `npm run typecheck`
- Verify Node.js version: `node --version`

### Database connection refused

**Symptoms**: `could not connect to server` errors

**Solutions**:
- Verify Supabase project is active
- Check `DATABASE_URL` format: `postgresql://user:pass@host:port/db`
- Ensure IP allowlisting includes your IP in Supabase dashboard
- Test connection: `psql $DATABASE_URL`

### AI provider errors

**Symptoms**: 401/403/429 from OpenAI/Anthropic/Gemini

**Solutions**:
- Verify API key is correct and active
- Check API key has required permissions
- Review rate limits: free tiers have strict limits
- Check provider status page for outages
- Verify billing is set up for paid tiers

## Authentication Issues

### Login fails with "Invalid credentials"

**Solutions**:
- Verify email/password are correct
- Check Supabase Auth is enabled
- Ensure user exists in Supabase dashboard
- Try password reset flow

### JWT token expired

**Symptoms**: 401 Unauthorized on authenticated requests

**Solutions**:
- Refresh the page to get new token
- Verify `JWT_SECRET_KEY` is consistent across deployments
- Check token expiration settings in Supabase

### CORS errors

**Symptoms**: Browser blocks API requests

**Solutions**:
- Verify `CORS_ORIGINS` in backend config includes frontend URL
- Check backend is running on expected port
- Ensure no proxy misconfiguration

## Performance Issues

### Slow response times

**Solutions**:
- Check database query performance: `EXPLAIN ANALYZE`
- Enable Redis caching for frequent queries
- Review AI provider latency
- Check for N+1 query patterns
- Monitor server resources: CPU, memory, disk I/O

### High memory usage

**Solutions**:
- Check for memory leaks in backend
- Review conversation history size
- Limit concurrent AI requests
- Scale horizontally with load balancer

### Rate limiting issues

**Symptoms**: 429 Too Many Requests

**Solutions**:
- Implement exponential backoff in client
- Cache responses where appropriate
- Upgrade to higher tier for increased limits
- Distribute load across multiple API keys

## Docker Issues

### Container exits immediately

**Solutions**:
- Check logs: `docker logs <container-name>`
- Verify environment variables are passed correctly
- Ensure volumes are mounted properly
- Check Docker Compose file syntax

### Database migration fails in Docker

**Solutions**:
- Ensure database container is healthy: `docker-compose ps`
- Run migrations manually: `docker-compose exec backend alembic upgrade head`
- Check migration file syntax

## Data Issues

### Messages not persisting

**Solutions**:
- Verify database tables exist
- Check Row Level Security policies in Supabase
- Review backend logs for database errors
- Test database connection directly

### Duplicate messages

**Solutions**:
- Check for duplicate API requests from frontend
- Verify idempotency keys are implemented
- Review WebSocket reconnection logic

## Getting Help

If you're still stuck:

1. Search [GitHub Issues](https://github.com/astrovox/astrovox/issues)
2. Check [Discussions](https://github.com/astrovox/astrovox/discussions)
3. Review [Support Documentation](./SUPPORT.md)
4. Contact support: support@astrovox.ai
