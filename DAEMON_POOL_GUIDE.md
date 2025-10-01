# FDO Daemon Pool Architecture Guide

## Overview

The FDO Daemon Pool provides enhanced resiliency for AtomForge by running multiple daemon instances in parallel, offering automatic failover and crash recovery. This solves the single point of failure issue where malformed payloads could crash the daemon and halt all operations.

## Key Features

- **Multiple Daemon Instances**: Configurable pool of daemon instances (default: 5)
- **Round-Robin Load Balancing**: Distributes requests across healthy daemons
- **Automatic Failover**: Seamlessly switches to healthy daemons when one crashes
- **Health Monitoring**: Continuous health checks with automatic restart of failed daemons
- **Circuit Breaker Pattern**: Prevents cascading failures by temporarily isolating failed daemons
- **Request Retry Logic**: Built-in retry with exponential backoff
- **Zero Downtime**: Hot replacement of crashed instances

## Configuration

### Environment Variables

```bash
# Enable/disable pool mode (default: true)
FDO_DAEMON_POOL_ENABLED=true

# Number of daemon instances (default: 5)
FDO_DAEMON_POOL_SIZE=5

# Starting port number (default: 8080)
# Daemons will use ports 8080, 8081, 8082, etc.
FDO_DAEMON_POOL_BASE_PORT=8080

# Daemon restart settings
FDO_DAEMON_RESTART_DELAY=2.0           # Seconds before restart attempt
FDO_DAEMON_HEALTH_INTERVAL=10.0       # Health check frequency (seconds)
FDO_DAEMON_MAX_RESTART_ATTEMPTS=5     # Max restart attempts per daemon

# Request retry settings
FDO_DAEMON_MAX_RETRIES=3               # Request retry attempts

# Optional: Per-daemon logging
FDO_DAEMON_LOG_TEMPLATE=/tmp/daemon_{id}.log
```

### Legacy Single Daemon Mode

To use the original single daemon mode:

```bash
FDO_DAEMON_POOL_ENABLED=false
FDO_DAEMON_PORT=8080
FDO_DAEMON_LOG=/tmp/daemon.log
```

## API Endpoints

### Health Monitoring

- **GET /health** - Overall service health with pool status
- **GET /health/pool** - Detailed pool health information
- **POST /pool/reset-circuit-breakers** - Reset all circuit breakers

### Pool Health Response Example

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
      "consecutive_failures": 0
    }
  ]
}
```

## Resilience Benefits

### Before (Single Daemon)
- Single point of failure
- One malformed payload crashes entire service
- Manual intervention required for recovery
- All requests fail during daemon restart

### After (Daemon Pool)
- Fault isolation - one crash doesn't halt service
- Automatic recovery without manual intervention
- Load distribution for better performance
- Graceful degradation with reduced capacity
- Built-in retry and failover logic

## Usage Examples

### Docker Compose
```yaml
environment:
  - FDO_DAEMON_POOL_ENABLED=true
  - FDO_DAEMON_POOL_SIZE=5
  - FDO_DAEMON_POOL_BASE_PORT=8080
```

### Monitoring Pool Health

```bash
# Check overall health
curl http://localhost:8000/health

# Get detailed pool information
curl http://localhost:8000/health/pool

# Reset circuit breakers if needed
curl -X POST http://localhost:8000/pool/reset-circuit-breakers
```

## Performance Considerations

- **Memory Usage**: Each daemon instance uses ~50-100MB
- **Port Usage**: Pool requires consecutive ports (8080, 8081, etc.)
- **Startup Time**: Pool initialization takes slightly longer than single daemon
- **CPU**: Health monitoring uses minimal CPU overhead

## Troubleshooting

### Common Issues

1. **No healthy daemons available**
   - Check daemon binary exists and is executable
   - Verify Wine is properly configured
   - Check port availability
   - Review daemon logs

2. **Frequent daemon restarts**
   - Increase `FDO_DAEMON_MAX_RESTART_ATTEMPTS`
   - Check for memory issues
   - Review malformed payload patterns

3. **Circuit breakers opening**
   - Use `/pool/reset-circuit-breakers` endpoint
   - Investigate root cause of failures
   - Adjust pool size if needed

### Monitoring Commands

```bash
# Watch pool health in real-time
watch -n 5 'curl -s http://localhost:8000/health/pool | jq .instances_by_state'

# Check daemon processes
ps aux | grep fdo_daemon
```

## Migration from Single Daemon

The pool implementation is backward compatible. Existing code will work without changes when pool mode is enabled. The pool client provides the same interface as the single daemon client.

To migrate:
1. Set `FDO_DAEMON_POOL_ENABLED=true`
2. Configure pool size and settings
3. Restart the service
4. Monitor pool health at `/health/pool`

## Technical Architecture

- **FdoDaemonPoolManager**: Manages multiple daemon instances
- **FdoDaemonPoolClient**: Provides failover and retry logic
- **Health Monitor**: Background thread for daemon health checks
- **Circuit Breakers**: Per-daemon failure protection
- **Round-Robin Selection**: Load balancing algorithm

The pool architecture maintains full API compatibility while providing enhanced resiliency and better handling of malformed payloads that could crash individual daemon instances.