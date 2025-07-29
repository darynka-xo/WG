# PDF OCR Extractor - Docker Deployment Guide

This guide explains how to deploy the PDF OCR Extractor application using Docker and Docker Compose.

## Prerequisites

- Docker Engine 20.10 or higher
- Docker Compose 2.0 or higher
- OpenAI API key (required for AI processing)
- At least 4GB RAM (recommended 8GB for better performance)
- At least 5GB free disk space for Docker images and data

## Quick Start

### 1. Clone and Setup

```bash
# Clone your repository (or copy files to your server)
cd finalOCRversion

# Copy environment file and configure
cp .env.example .env
```

### 2. Configure Environment

Edit the `.env` file and add your OpenAI API key:

```bash
# Required: Add your OpenAI API key
OPENAI_API_KEY=sk-your-actual-openai-api-key-here

# Optional: Adjust cleanup settings
CLEANUP_HOURS=1
CLEANUP_INTERVAL=300
```

### 3. Deploy Application

```bash
# Build and start the application
docker-compose up -d

# View logs
docker-compose logs -f ocr-app
```

### 4. Access Application

- **Direct access**: http://localhost:8000
- **Through existing nginx**: http://your-server-ip (if you have nginx configured on host)

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | - | **Required**: Your OpenAI API key |
| `CLEANUP_HOURS` | 1 | Hours before files are auto-deleted |
| `CLEANUP_INTERVAL` | 300 | Cleanup check interval in seconds |

### Volume Mounts

The application creates persistent volumes for:

- `./docker-volumes/uploads/` - Uploaded PDF files
- `./docker-volumes/results/` - Processing results and extracted data
- `./docker-volumes/temp/` - Temporary files
- `./docker-volumes/static/` - Generated static files (OCR overlays, etc.)

## Production Deployment

### Using Existing Nginx on Host

If you already have nginx running on your host system (like Ubuntu 22.04), you can use your existing configuration. The Docker container will expose port 8000, and your nginx can proxy to it.

Example nginx configuration (add to your existing nginx sites):
```nginx
server {
    listen 80;
    server_name _;  # or your domain

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
    }
}
```

Then reload nginx: `sudo systemctl reload nginx`

### 2. Security Considerations

- **Firewall**: Only expose ports 80, 443 to the internet
- **API Key**: Store OpenAI API key securely in .env file
- **File uploads**: Default limit is 100MB (configurable in your nginx configuration)
- **Auto-cleanup**: Enabled by default to prevent disk filling

### 3. Monitoring

```bash
# Check application health
curl http://localhost:8000/health

# Monitor resource usage
docker stats pdf-ocr-extractor

# View cleanup status
curl http://localhost:8000/cleanup/status
```

## Management Commands

### Service Management

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart application only
docker-compose restart ocr-app

# View logs
docker-compose logs -f ocr-app

# Update application (after code changes)
docker-compose build ocr-app
docker-compose up -d ocr-app
```

### Data Management

```bash
# Backup data volumes
tar -czf backup-$(date +%Y%m%d).tar.gz docker-volumes/

# Clean up old containers and images
docker system prune -a

# Manual cleanup of application data
curl -X DELETE http://localhost:8000/cleanup/{upload_id}
```

### Troubleshooting

```bash
# Check container status
docker-compose ps

# View application logs
docker-compose logs ocr-app

# Check disk space
df -h
du -sh docker-volumes/

# Restart all services
docker-compose down && docker-compose up -d

# Rebuild from scratch
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Resource Requirements

### Minimum Requirements

- **CPU**: 2 cores
- **RAM**: 4GB
- **Disk**: 10GB free space
- **Network**: Internet access for OpenAI API

### Recommended for Production

- **CPU**: 4+ cores
- **RAM**: 8GB+
- **Disk**: 50GB+ SSD
- **Network**: Stable internet with good bandwidth

## API Endpoints

Once deployed, the application provides these key endpoints:

- `GET /` - Web interface
- `POST /upload` - Upload and process PDF
- `GET /results/{upload_id}` - Get processing results
- `GET /download/{upload_id}/{file_type}/{filename}` - Download files
- `GET /ocr-viewer/{upload_id}` - Interactive OCR viewer
- `GET /health` - Health check endpoint

## Support and Maintenance

### Regular Maintenance

1. **Monitor disk usage**: Auto-cleanup helps, but monitor `/docker-volumes/`
2. **Check logs regularly**: `docker-compose logs -f`
3. **Update dependencies**: Rebuild periodically with `--no-cache`
4. **Backup data**: Regular backups of `docker-volumes/` directory

### Performance Tuning

- **Increase cleanup frequency** for high-volume usage
- **Adjust nginx worker processes** based on CPU cores
- **Monitor memory usage** and adjust container limits if needed
- **Use SSD storage** for better I/O performance

### Scaling

For high-volume deployments:

1. **Load balancer**: Use multiple app instances
2. **Shared storage**: Move volumes to network storage
3. **Queue system**: Add Redis/Celery for background processing
4. **Database**: Add PostgreSQL for metadata storage

## Security Best Practices

1. **API Key Security**: 
   - Never commit API keys to version control
   - Use environment files or Docker secrets
   - Rotate keys regularly

2. **Network Security**:
   - Use firewall to restrict access
   - Consider VPN for admin access
   - Enable SSL/TLS for production

3. **File Security**:
   - Auto-cleanup prevents data accumulation
   - Regular backup and secure deletion
   - Monitor for unusual upload patterns

4. **Container Security**:
   - Keep base images updated
   - Run containers as non-root user (future enhancement)
   - Regular security scans

## License and Support

This deployment configuration is provided as-is. For issues:

1. Check application logs: `docker-compose logs ocr-app`
2. Verify environment configuration
3. Ensure OpenAI API key is valid and has credits
4. Check system resources (disk space, memory)

For additional support, consult the application documentation or create an issue in the project repository. 