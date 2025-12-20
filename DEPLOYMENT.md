# Deploying Catwalk Live to Production

Guide for deploying the backend to Fly.io and optionally deploying the frontend.

## Prerequisites

- **Fly.io account** ([Sign up](https://fly.io/app/sign-up))
- **Fly CLI** installed ([Install guide](https://fly.io/docs/hands-on/install-flyctl/))
- **Fly.io auth token** (run `fly auth login`)

## Backend Deployment to Fly.io

### 1. Create Fly.io Apps

```bash
# Create backend app
fly apps create <your-backend-app> --org your-org-name

# Create PostgreSQL database
fly postgres create --name <your-database-app> --region <region>
# Recommended regions: sjc (San Jose), ord (Chicago), lax (Los Angeles)
# See: https://fly.io/docs/reference/regions/
```

### 2. Attach Database

```bash
cd backend
fly postgres attach <your-database-app> --app <your-backend-app>
```

This automatically sets the `DATABASE_URL` secret.

### 3. Set Required Secrets

```bash
# Generate encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Set secrets
fly secrets set ENCRYPTION_KEY="<generated-key>" --app <your-backend-app>
fly secrets set OPENROUTER_API_KEY="sk-or-v1-..." --app <your-backend-app>
fly secrets set PUBLIC_URL="https://<your-backend-app>.fly.dev" --app <your-backend-app>
```

**Optional (for MCP server deployments)**:
```bash
fly secrets set FLY_API_TOKEN="<your-fly-token>" --app <your-backend-app>
fly secrets set FLY_MCP_APP_NAME="<your-mcp-app>" --app <your-backend-app>
fly secrets set FLY_MCP_IMAGE="registry.fly.io/<your-backend-app>:mcp-host" --app <your-backend-app>
```

### 4. Update fly.toml

Edit `backend/fly.toml`:

```toml
app = '<your-backend-app>'
primary_region = '<your-region>'  # e.g., 'sjc', 'ord', 'lax'

# Rest of file stays the same
```

### 5. Deploy!

```bash
cd backend
fly deploy --app <your-backend-app>
```

**First deployment** runs database migrations automatically via `release_command`.

### 6. Verify Deployment

```bash
# Check health
curl https://<your-backend-app>.fly.dev/api/health

# View logs
fly logs --app <your-backend-app>

# Check status
fly status --app <your-backend-app>
```

## Frontend Deployment Options

### Option A: Vercel (Recommended)

1. **Connect to GitHub**:
   - Go to [Vercel](https://vercel.com/)
   - Import your fork of `zenchantlive/catwalk`
   - Select the `frontend` directory as root

2. **Configure Environment**:
   - Set `NEXT_PUBLIC_API_URL` to your backend URL:
     ```
     NEXT_PUBLIC_API_URL=https://<your-backend-app>.fly.dev/api/:path*
     ```

3. **Deploy**: Vercel auto-deploys on every push to `main`

### Option B: Fly.io (Manual)

1. **Create frontend app**:
   ```bash
   cd frontend
   fly apps create <your-frontend-app>
   ```

2. **Create `Dockerfile`** (Nextjs on Fly.io)

3. **Deploy**:
   ```bash
   fly deploy --app <your-frontend-app>
   ```

### Option C: Local Frontend + Production Backend

Just run `bun run dev` locally and configure `.env.local`:

```
NEXT_PUBLIC_API_URL=https://<your-backend-app>.fly.dev/api/:path*
```

## Troubleshooting

### Database Connection Issues

**Error**: `psycopg.OperationalError: connection failed`

**Fix**:
```bash
# Check database status
fly status --app <your-database-app>

# View database logs
fly logs --app <your-database-app>

# Verify DATABASE_URL is set
fly secrets list --app <your-backend-app>

# If missing, manually attach
fly postgres attach <your-database-app> --app <your-backend-app>
```

### Health Checks Failing

**Error**: App keeps restarting, health checks fail

**Debug**:
```bash
# View logs
fly logs --app <your-backend-app>

# Common causes:
# 1. Database migrations failing (check DATABASE_URL)
# 2. Missing secrets (ENCRYPTION_KEY, OPENROUTER_API_KEY)
# 3. Wrong port (must be 8080)
# 4. Import errors (missing dependencies in requirements.txt)
```

**Fix**:
```bash
# SSH into container to debug
fly ssh console --app <your-backend-app>

# Inside container, check:
python -c "import app.main"  # Should not error
```

### "No Active Leader Found" (Postgres)

**Error**: `Error: no active leader found`

**This means your Postgres cluster is broken**. The only fix is to recreate it:

```bash
# 1. Destroy broken database
fly apps destroy <your-database-app>

# 2. Create fresh database
fly postgres create --name <your-database-app> --region <region>

# 3. Re-attach to backend
fly postgres attach <your-database-app> --app <your-backend-app>

# 4. Redeploy backend (runs migrations)
fly deploy --app <your-backend-app>
```

### Missing Python Dependencies

**Error**: `ModuleNotFoundError: No module named 'xyz'`

**Fix**:
1. Add package to `backend/requirements.txt`
2. Redeploy: `fly deploy --app <your-backend-app>`

### Build Failures

**Error**: Docker build fails during `fly deploy`

**Debug locally**:
```bash
cd backend
docker build -t catwalk-backend .
```

**If build succeeds locally, try**:
```bash
fly deploy --no-cache --app <your-backend-app>
```

## Scaling & Performance

### Vertical Scaling (More RAM/CPU)

```bash
# Scale to 1GB RAM, dedicated CPU
fly scale vm dedicated-cpu-1x --app <your-backend-app>

# Scale to 2GB RAM
fly scale memory 2048 --app <your-backend-app>
```

### Horizontal Scaling (More Instances)

```bash
# Run 2 instances (auto load-balanced)
fly scale count 2 --app <your-backend-app>
```

### Database Scaling

```bash
# Upgrade to larger database
fly postgres create --name <new-db-app> --vm-size dedicated-cpu-2x

# Migrate data (see Fly.io docs)
```

## Costs

**Estimated monthly costs** (as of 2025):

| Component | Configuration | Cost |
|-----------|---------------|------|
| Backend | 512MB RAM, shared CPU, always-on | ~$5/month |
| Database | 256MB RAM, single-node | ~$3/month |
| Frontend (Vercel) | Hobby plan | Free |
| MCP deployments | Per machine, hourly billing | ~$0.02/hour each |

**See**: [Fly.io Pricing](https://fly.io/docs/about/pricing/)

## Security Best Practices

1. **Rotate secrets regularly**:
   ```bash
   fly secrets set ENCRYPTION_KEY="<new-key>" --app <your-backend-app>
   ```

2. **Use internal networking**:
   - Fly apps can communicate via `<app-name>.internal` (no public internet)

3. **Enable SSL/TLS**:
   - Fly.io provides free SSL certificates automatically

4. **Monitor logs**:
   ```bash
   fly logs --app <your-backend-app> | grep ERROR
   ```

5. **Set up alerts**: Use Fly.io monitoring or external services (Sentry, etc.)

## Backup & Recovery

### Database Backups

```bash
# Fly.io auto-backups Postgres daily

# Manual backup
fly postgres db backup <your-database-app>

# Restore from backup (see Fly.io docs)
```

### Rollback Deployment

```bash
# List previous releases
fly releases --app <your-backend-app>

# Rollback to specific version
fly releases rollback <version> --app <your-backend-app>
```

## Next Steps

- Set up monitoring (Sentry, Datadog, etc.)
- Configure custom domain (Fly.io supports this)
- Enable auto-scaling based on traffic
- Set up staging environment

## Resources

- [Fly.io Documentation](https://fly.io/docs/)
- [Fly Machines API](https://fly.io/docs/machines/api/)
- [PostgreSQL on Fly.io](https://fly.io/docs/postgres/)
- [Fly.io Regions](https://fly.io/docs/reference/regions/)

Need help? Open an issue on GitHub!
