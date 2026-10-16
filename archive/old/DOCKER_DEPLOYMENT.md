# Docker Deployment Guide

This guide provides comprehensive instructions for deploying the LLM Evaluation Stack using Docker Compose.

## Overview

The Docker Compose orchestration provides a complete deployment including:

- **Ollama Service**: Local LLM backend for model hosting
- **Go Service**: High-performance evaluation proxy with database
- **Python Service**: Main evaluation engine with web interface
- **Prometheus**: Metrics collection and monitoring
- **Grafana**: Dashboard and visualization
- **Nginx**: Reverse proxy and load balancing

## Quick Start

### Development Environment

```bash
# Clone the repository
git clone <repository-url>
cd llm-evals

# Start development environment
./docker/scripts/setup.sh

# Access the interface
open http://localhost:8000/unified
```

### Production Environment

```bash
# Setup production environment
cp .env.prod .env
./docker/scripts/deploy.sh prod

# Access the interface
open http://localhost
```

## Directory Structure

```
docker/
├── docker-compose.yml              # Main orchestration file
├── docker-compose.dev.yml          # Development overrides
├── docker-compose.prod.yml         # Production overrides
├── python/
│   ├── Dockerfile                  # Python service container
│   ├── Dockerfile.dev              # Development container
│   └── requirements.txt            # Additional dependencies
├── nginx/
│   ├── Dockerfile                  # Nginx reverse proxy
│   ├── nginx.conf                  # Default configuration
│   └── nginx.prod.conf             # Production configuration
├── prometheus/
│   ├── prometheus.yml              # Default configuration
│   ├── prometheus.dev.yml          # Development configuration
│   └── prometheus.prod.yml         # Production configuration
├── grafana/
│   ├── dashboards/                 # Dashboard provisioning
│   │   └── dashboard.yml
│   └── datasources/                # Data source configuration
│       └── prometheus.yml
└── scripts/
    ├── setup.sh                    # Initial setup script
    ├── deploy.sh                   # Production deployment
    └── health-check.sh             # Health monitoring
```

## Configuration

### Environment Files

#### Development (.env.dev)
```env
ENABLE_GO_SERVICE=true
ENABLE_LOCAL_MODELS=true
LOG_LEVEL=debug
OLLAMA_MODELS=llama3.2:3b,gemma3:1b
```

#### Production (.env.prod)
```env
ENABLE_GO_SERVICE=true
ENABLE_LOCAL_MODELS=true
LOG_LEVEL=info
OLLAMA_MODELS=llama3.3:8b,gemma3:27b,phi4-reasoning
GRAFANA_ADMIN_PASSWORD=secure_password
```

### Service Configuration

#### Ollama Configuration
- **Models**: Configurable via `OLLAMA_MODELS` environment variable
- **Concurrency**: Controlled by `OLLAMA_NUM_PARALLEL`
- **Memory**: Managed by `OLLAMA_MAX_LOADED_MODELS`

#### Go Service Configuration
- **Database**: SQLite database in persistent volume
- **Metrics**: Prometheus metrics exposed on `/metrics`
- **Health**: Health check on `/health`

#### Python Service Configuration
- **Workers**: Configurable via `WORKERS` environment variable
- **Monitoring**: Integrated health checks and metrics
- **API**: Full REST API and WebSocket support

## Deployment

### Development Deployment

```bash
# Start development environment
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# View logs
docker-compose logs -f python-service

# Access services
curl http://localhost:8000/health
curl http://localhost:8080/health
curl http://localhost:11434/api/tags
```

### Production Deployment

```bash
# Deploy to production
./docker/scripts/deploy.sh prod

# Monitor deployment
./docker/scripts/health-check.sh

# View service status
docker-compose ps
```

### Scaling Services

```bash
# Scale Python service
docker-compose up -d --scale python-service=3

# Scale with load balancer
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --scale python-service=2
```

## Monitoring

### Service Health Checks

All services include comprehensive health checks:

```bash
# Check individual service health
curl http://localhost:8000/health    # Python service
curl http://localhost:8080/health    # Go service
curl http://localhost:11434/api/tags # Ollama
curl http://localhost:80/health      # Nginx
```

### Prometheus Metrics

Access metrics at:
- Go Service: `http://localhost:8080/metrics`
- Python Service: `http://localhost:8000/metrics`
- Prometheus: `http://localhost:9090`

### Grafana Dashboard

Access dashboard at `http://localhost:3000/grafana`
- Username: `admin`
- Password: Set via `GRAFANA_ADMIN_PASSWORD`

## Troubleshooting

### Common Issues

#### Services Not Starting

```bash
# Check service logs
docker-compose logs ollama
docker-compose logs go-service
docker-compose logs python-service

# Check resource usage
docker stats

# Restart services
docker-compose restart [service-name]
```

#### Health Check Failures

```bash
# Run comprehensive health check
./docker/scripts/health-check.sh

# Check specific service
curl -v http://localhost:8000/health
```

#### Model Download Issues

```bash
# Check Ollama status
docker-compose exec ollama ollama list

# Manually download models
docker-compose exec ollama ollama pull llama3.2:3b
```

#### Database Issues

```bash
# Check Go service database
docker-compose exec go-service ls -la /data/

# Reset database
docker-compose stop go-service
docker volume rm llm-evals_go_data
docker-compose up -d go-service
```

### Performance Optimization

#### Resource Allocation

```yaml
# docker-compose.prod.yml
services:
  ollama:
    deploy:
      resources:
        limits:
          memory: 8G
        reservations:
          memory: 4G
```

#### Networking

```yaml
networks:
  llm-eval-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

## Security

### Network Security

- Services communicate through internal Docker network
- Nginx reverse proxy provides single entry point
- Rate limiting configured for API endpoints

### Container Security

- Non-root users in all containers
- Minimal base images (Alpine Linux)
- Security headers in Nginx configuration

### Secrets Management

```bash
# Use environment variables for secrets
export GRAFANA_ADMIN_PASSWORD="secure_password"
export OPENROUTER_API_KEY="your_api_key"
```

## Backup and Recovery

### Data Backup

```bash
# Backup volumes
docker run --rm -v llm-evals_ollama_data:/data -v $(pwd):/backup alpine tar czf /backup/ollama-backup.tar.gz /data
docker run --rm -v llm-evals_go_data:/data -v $(pwd):/backup alpine tar czf /backup/go-backup.tar.gz /data
```

### Recovery

```bash
# Restore volumes
docker volume create llm-evals_ollama_data
docker run --rm -v llm-evals_ollama_data:/data -v $(pwd):/backup alpine tar xzf /backup/ollama-backup.tar.gz -C /
```

## Updates and Maintenance

### Updating Services

```bash
# Pull latest images
docker-compose pull

# Recreate containers
docker-compose up -d --force-recreate

# Clean up old images
docker image prune -f
```

### Log Management

```bash
# View logs
docker-compose logs -f --tail=100

# Rotate logs
docker-compose logs --since="24h" > logs/docker-$(date +%Y%m%d).log
```

## Integration with Make

The Docker deployment integrates with the existing Make system:

```bash
# Run tests with Docker stack
make test-docker

# Start Docker development environment
make docker-dev

# Deploy to production
make docker-prod
```

## Support and Troubleshooting

For issues:
1. Check service logs: `docker-compose logs [service]`
2. Run health checks: `./docker/scripts/health-check.sh`
3. Review resource usage: `docker stats`
4. Check network connectivity: `docker network ls`

For more detailed troubleshooting, see the main troubleshooting documentation.