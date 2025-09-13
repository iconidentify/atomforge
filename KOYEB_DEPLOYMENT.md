# 🚀 Deploy FDO API to Koyeb

Deploy your FDO compilation API to Koyeb's free tier with automatic scaling and SSL certificates.

## Quick Start (3 Minutes)

### Option A: GitHub Integration (Easiest)

1. **Sign up for Koyeb**: https://app.koyeb.com/auth/signup
2. **Connect GitHub**: Go to Services → Create Service → GitHub
3. **Select Repository**: Choose `iconidentify/ada32-toolkit`
4. **Configure Deployment**:
   - **Branch**: `master`
   - **Work Directory**: `api`
   - **Dockerfile**: `api/Dockerfile.koyeb`
   - **Port**: `8000`
   - **Instance Type**: `Free` (512MB RAM, 0.1 vCPU)
5. **Deploy**: Click "Deploy"

**✅ Done!** Your API will be live at `https://your-app.koyeb.app`

### Option B: GitHub Actions (Automated)

For automated deployments on every push:

1. **Get Koyeb API Keys**:
   ```bash
   # In Koyeb dashboard: Settings → API
   # Generate Public and Private keys
   ```

2. **Add to GitHub Secrets**:
   - Go to your repo → Settings → Secrets and variables → Actions
   - Add: `KOYEB_PUBLIC_KEY` and `KOYEB_PRIVATE_KEY`

3. **Trigger Deployment**:
   - Push to `master` branch (auto-deploys)
   - Or use manual trigger in GitHub Actions

## API Usage

Once deployed, your API is available at: `https://your-app.koyeb.app`

### Test the API

```bash
# Health check
curl https://your-app.koyeb.app/health

# Compile FDO (example)
curl -X POST https://your-app.koyeb.app/compile \
  -H "Content-Type: application/json" \
  -d '{
    "source": "uni_start_stream <00x>\n  man_start_object <independent, \"Hello World\">\n    man_add_button <\"OK\", 100, 100, 50, 30>\n  man_end_object <>\nman_end_stream <>"
  }' \
  --output hello.fdo
```

### Swagger Documentation

- **Interactive API Docs**: https://your-app.koyeb.app/
- **OpenAPI Spec**: https://your-app.koyeb.app/openapi.json

## Configuration

### Environment Variables

```yaml
# Optional: Configure logging level
LOG_LEVEL: INFO  # DEBUG, INFO, WARNING, ERROR

# Optional: Configure Python path
PYTHONPATH: /app
```

### Resource Allocation (Free Tier)

- **CPU**: 0.1 vCPU
- **RAM**: 512MB
- **Storage**: Ephemeral (resets on redeploy)
- **Scaling**: Single instance (free tier limit)

## Troubleshooting

### Deployment Issues

**Build Fails**:
```bash
# Check build logs in Koyeb dashboard
# Common issues:
# - Missing dependencies in requirements.txt
# - Wine initialization problems
# - Port conflicts (use 8000)
```

**API Won't Start**:
```bash
# Check container logs
curl https://your-app.koyeb.app/health

# If 500 error, check:
# - Wine is properly initialized
# - Ada32.dll files are present
# - Python dependencies are installed
```

### Common Errors

**Wine Initialization**:
```
# In Dockerfile.koyeb, ensure:
RUN Xvfb :99 -screen 0 800x600x16 > /dev/null 2>&1 & \
    sleep 3 && \
    wine wineboot --init
```

**Missing Dependencies**:
```bash
# Check api/requirements.txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
```

## Advanced Configuration

### Custom Domain

1. Go to Koyeb Dashboard → Your Service → Settings
2. Add custom domain
3. Configure DNS (CNAME record)

### Environment-Specific Deployments

Use GitHub Actions inputs for different environments:

```yaml
# In .github/workflows/deploy-koyeb.yml
KOYEB_APP_NAME: fdo-api-${{ github.event.inputs.environment }}
```

### Monitoring & Logs

- **Real-time Logs**: Koyeb Dashboard → Your Service → Logs
- **Metrics**: CPU, Memory, Network usage
- **Health Checks**: Automatic `/health` endpoint monitoring

## Cost Optimization

### Free Tier Limits
- ✅ 1 always-on service
- ✅ 512MB RAM, 0.1 vCPU
- ✅ Unlimited bandwidth
- ✅ Automatic SSL certificates

### Upgrade Options
- **Starter**: $5/month (1GB RAM, 0.5 vCPU)
- **Hobby**: $15/month (2GB RAM, 1 vCPU)
- **Pro**: $30/month (4GB RAM, 2 vCPU)

## Security

### Built-in Security Features
- ✅ Automatic SSL/TLS certificates
- ✅ DDoS protection
- ✅ Web Application Firewall (WAF)
- ✅ Automatic security updates

### API Security Best Practices
```python
# Add to api_server.py for production
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Backup & Recovery

### Automatic Backups
- ✅ Code: GitHub repository
- ✅ Configuration: Koyeb dashboard export
- ✅ Database: N/A (stateless API)

### Manual Backup
```bash
# Export service configuration
koyeb services export your-service-name

# Backup environment variables
koyeb services env list your-service-name
```

## Support

- **Koyeb Documentation**: https://docs.koyeb.com/
- **GitHub Issues**: Report bugs in the repository
- **Community**: https://community.koyeb.com/

---

## 🎉 Success!

Your FDO compilation API is now running on Koyeb with:

- ✅ **Zero configuration** deployment
- ✅ **Free tier** hosting
- ✅ **Automatic SSL** certificates
- ✅ **Global CDN** distribution
- ✅ **Real-time monitoring**
- ✅ **Professional API** with Swagger docs

**Share your API URL and start compiling FDO files in the cloud!** 🚀
