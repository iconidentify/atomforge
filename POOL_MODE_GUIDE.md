# AtomForge Daemon Pool Mode - Complete Guide

## Overview

Daemon Pool Mode allows AtomForge to run multiple `fdo_daemon.exe` instances in parallel, dramatically improving throughput for simultaneous requests. This is especially beneficial for large DOD payloads and concurrent chunking operations.

## When to Use Pool Mode

### Use Pool Mode If:
- You have **concurrent users** making simultaneous requests
- You process **large DOD payloads** that take significant time
- You need **high availability** with automatic failover
- You want **resilience** against individual daemon crashes

### Stick with Single Daemon Mode If:
- You have **low request volume** (< 10 requests/minute)
- You have **limited memory** (< 512MB available)
- You want **minimal resource usage**
- You're **testing** or in development

## Quick Start

### 1. Enable Pool Mode

Edit `docker-compose.yml`:

```yaml
environment:
  - FDO_DAEMON_POOL_ENABLED=true  # Enable pool mode
  - FDO_DAEMON_POOL_SIZE=5        # Number of daemons
  - FDO_DAEMON_POOL_BASE_PORT=8080
```

### 2. Increase Memory Limits

Pool mode requires more memory:

```yaml
deploy:
  resources:
    limits:
      memory: 1G   # Required for pool_size=5
      cpus: '1.0'
```

### 3. Restart Service

```bash
docker compose down
docker compose up --build
```

### 4. Verify Pool Status

Check http://localhost:8000/pool or:

```bash
curl http://localhost:8000/health/pool
```

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FDO_DAEMON_POOL_ENABLED` | `false` | Enable pool mode |
| `FDO_DAEMON_POOL_SIZE` | `5` | Number of daemon instances (1-20) |
| `FDO_DAEMON_POOL_BASE_PORT` | `8080` | Starting port (uses BASE_PORT + 0, 1, 2...) |
| `FDO_DAEMON_HEALTH_INTERVAL` | `10.0` | Health check frequency (seconds) |
| `FDO_DAEMON_RESTART_DELAY` | `2.0` | Delay before restart (seconds) |
| `FDO_DAEMON_MAX_RESTART_ATTEMPTS` | `5` | Max restart attempts per daemon |
| `FDO_DAEMON_MAX_RETRIES` | `3` | Request retry attempts |
| `FDO_DAEMON_REQUEST_TIMEOUT` | `10.0` | Timeout per request (seconds) |
| `FDO_DAEMON_CIRCUIT_BREAKER_THRESHOLD` | `3` | Failures before opening circuit breaker |

### Example Configurations

#### Small Pool (Memory Constrained)
```yaml
- FDO_DAEMON_POOL_ENABLED=true
- FDO_DAEMON_POOL_SIZE=2
memory: 512M
```

#### Medium Pool (Recommended)
```yaml
- FDO_DAEMON_POOL_ENABLED=true
- FDO_DAEMON_POOL_SIZE=5
memory: 1G
```

#### Large Pool (High Traffic)
```yaml
- FDO_DAEMON_POOL_ENABLED=true
- FDO_DAEMON_POOL_SIZE=10
memory: 2G
```

## Architecture

### Load Balancing

Requests are distributed using **round-robin** selection:

```
Request 1 → daemon_0
Request 2 → daemon_1
Request 3 → daemon_2
Request 4 → daemon_3
Request 5 → daemon_4
Request 6 → daemon_0  (cycles back)
```

### Failover & Retry

If a daemon fails:

1. Request automatically retries on next healthy daemon
2. Failed daemon is marked unhealthy
3. Circuit breaker opens after 3 consecutive failures
4. Automatic restart attempted (up to 5 times)
5. Exponential backoff between retries (0.1s, 0.2s, 0.4s...)

### Health Monitoring

Background thread checks all daemons every 10 seconds:

- **Healthy**: Daemon responding, circuit breaker closed
- **Unhealthy**: Daemon not responding, circuit breaker open
- **Crashed**: Daemon process dead, restart in progress
- **Restarting**: Daemon being restarted

### Circuit Breakers

Circuit breakers prevent cascading failures:

- Opens after **3 consecutive failures**
- Automatically closes when daemon becomes healthy
- Can be manually reset via API or web UI

## Web UI

Access the pool dashboard at: **http://localhost:8000/pool**

### Features

- **Real-time status** (auto-refreshes every 5 seconds)
- **Health visualization** with color-coded progress bar
- **Per-daemon metrics** (requests, failures, restarts)
- **Circuit breaker status** for each daemon
- **Manual circuit breaker reset** button

### Dashboard Metrics

| Metric | Description |
|--------|-------------|
| **Healthy Instances** | Number of healthy daemons / total |
| **Total Requests** | Sum of requests across all daemons |
| **Failed Requests** | Sum of failed requests |
| **Total Restarts** | Sum of daemon restarts |

## API Endpoints

### GET /health

Returns pool summary:

```json
{
  "status": "healthy",
  "execution_mode": "daemon_pool",
  "pool": {
    "enabled": true,
    "size": 5,
    "healthy_instances": 4,
    "health_percentage": 80.0
  }
}
```

### GET /health/pool

Returns detailed pool status:

```json
{
  "pool_size": 5,
  "instances_total": 5,
  "instances_healthy": 4,
  "pool_health_percentage": 80.0,
  "total_requests": 1250,
  "failed_requests": 15,
  "daemon_restarts": 2,
  "instances_by_state": {
    "healthy": 4,
    "unhealthy": 0,
    "crashed": 1,
    "restarting": 0
  },
  "instances": [
    {
      "id": "daemon_0",
      "port": 8080,
      "state": "healthy",
      "restart_count": 0,
      "consecutive_failures": 0,
      "total_requests": 250,
      "failed_requests": 0,
      "circuit_breaker_open": false,
      "last_health_check": 1730486123.45
    }
    // ... more instances
  ]
}
```

### POST /pool/reset-circuit-breakers

Reset all circuit breakers:

```bash
curl -X POST http://localhost:8000/pool/reset-circuit-breakers
```

Response:
```json
{
  "success": true,
  "circuit_breakers_reset": 2,
  "message": "Reset circuit breakers for 2 instance(s)"
}
```

## File System Layout

Each daemon gets an isolated working directory with symlinked files:

```
/tmp/fdo_daemon_pool/
├── daemon_0/
│   ├── fdo_daemon.exe → /atomforge/releases/.../fdo_daemon.exe
│   ├── Ada32.dll → /atomforge/releases/.../Ada32.dll
│   └── ... (other DLLs symlinked)
├── daemon_1/
│   └── ... (same structure)
└── daemon_4/
    └── ...
```

**Disk Usage**: ~35 inodes (negligible), symlinks don't duplicate data

## Performance Characteristics

### Throughput Comparison

| Pool Size | Concurrent Requests | Throughput Gain |
|-----------|---------------------|-----------------|
| 1 (single) | 1 | Baseline |
| 2 | 2-4 | 2x |
| 5 (default) | 5-10 | 5x |
| 10 | 10-20 | 10x |

### Memory Usage

| Pool Size | Expected Memory | Recommended Limit |
|-----------|-----------------|-------------------|
| 1 | 128-256 MB | 256 MB |
| 2 | 200-400 MB | 512 MB |
| 5 | 500-750 MB | 1 GB |
| 10 | 1-1.5 GB | 2 GB |

### Latency

- **Single request**: Same as single daemon (~50-200ms)
- **Concurrent requests**: Near-linear scaling up to pool size
- **Failover overhead**: < 500ms (time to switch daemons)

## Troubleshooting

### Problem: Pool fails to start

**Symptoms**: Service crashes on startup

**Solutions**:
1. Check memory limits: `docker stats atomforge-v2`
2. Reduce pool size: `FDO_DAEMON_POOL_SIZE=2`
3. Check port availability: `netstat -an | grep 8080`
4. View logs: `docker logs atomforge-v2`

### Problem: All circuit breakers open

**Symptoms**: All daemons show "⚠ OPEN" in UI

**Solutions**:
1. Reset circuit breakers via UI or API
2. Check daemon logs: `docker logs atomforge-v2`
3. Restart service: `docker compose restart`

### Problem: Daemons keep crashing

**Symptoms**: High restart count, "crashed" state

**Solutions**:
1. Check for malformed FDO input causing crashes
2. Increase `FDO_DAEMON_MAX_RESTART_ATTEMPTS`
3. Review Ada32.dll crash patterns in logs
4. Consider reducing pool size

### Problem: High memory usage

**Symptoms**: Docker OOM kills, service crashes

**Solutions**:
1. Reduce pool size: `FDO_DAEMON_POOL_SIZE=3`
2. Increase memory limit: `memory: 2G`
3. Check for memory leaks: `docker stats --no-stream`

## Migration Guide

### From Single Daemon to Pool Mode

1. **Backup current configuration**:
   ```bash
   cp docker-compose.yml docker-compose.yml.backup
   ```

2. **Update docker-compose.yml**:
   ```yaml
   - FDO_DAEMON_POOL_ENABLED=true
   - FDO_DAEMON_POOL_SIZE=5
   memory: 1G
   ```

3. **Restart service**:
   ```bash
   docker compose down
   docker compose up --build -d
   ```

4. **Verify health**:
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/health/pool
   ```

5. **Monitor for 24 hours**:
   - Check pool UI: http://localhost:8000/pool
   - Watch logs: `docker logs -f atomforge-v2`
   - Monitor memory: `docker stats atomforge-v2`

### Rollback to Single Daemon

1. **Edit docker-compose.yml**:
   ```yaml
   - FDO_DAEMON_POOL_ENABLED=false
   memory: 256M  # Optional: reduce back
   ```

2. **Restart**:
   ```bash
   docker compose restart
   ```

## Best Practices

### 1. Start Small
Begin with `POOL_SIZE=2`, increase gradually based on load

### 2. Monitor Health
Check `/health/pool` regularly, set up alerts for < 50% healthy

### 3. Right-size Pool
- **Low traffic**: 2-3 daemons
- **Medium traffic**: 5 daemons (default)
- **High traffic**: 7-10 daemons

### 4. Set Resource Limits
Always set memory limits to prevent OOM:
- `POOL_SIZE=2`: 512M
- `POOL_SIZE=5`: 1G
- `POOL_SIZE=10`: 2G

### 5. Handle Circuit Breakers
Reset circuit breakers during maintenance windows or after fixing issues

### 6. Plan for Failures
With pool mode, individual daemon failures are transparent to clients

## Production Checklist

Before deploying pool mode to production:

- [ ] Memory limit increased to support pool size
- [ ] Health monitoring configured
- [ ] Alert thresholds set (< 50% healthy)
- [ ] Backup configuration saved
- [ ] Rollback plan tested
- [ ] Load testing completed
- [ ] Team trained on pool UI
- [ ] Circuit breaker reset procedure documented

## Support & Feedback

- **Logs**: `docker logs atomforge-v2`
- **Pool Status**: http://localhost:8000/pool
- **API Health**: http://localhost:8000/health/pool
- **Issues**: File bug reports with pool status JSON

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-01 | Initial pool mode implementation |
