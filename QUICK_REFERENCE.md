# Jasmin Web Panel - Quick Reference Card

## 🔗 Access URLs

| Service | URL/Host | Port | Credentials |
|---------|----------|------|-------------|
| **Web Panel** | http://16.16.92.247:8999 | 8999 | admin / secret |
| **Jasmin Dashboard** | 16.16.92.247 | 8990 | jcliadmin / jclipwd |
| **SMPP Gateway** | 16.16.92.247 | 2775 | - |
| **HTTP API** | http://16.16.92.247:1401 | 1401 | - |

## 🔑 SSH Access

```bash
ssh -i jasmin-web-key.pem ubuntu@16.16.92.247
cd jasmin-web-panel
```

## 🐳 Docker Commands

```bash
# View all services
docker compose ps

# View logs (all services)
docker compose logs -f

# View logs (specific service)
docker compose logs -f jasmin-web
docker compose logs -f jasmin
docker compose logs -f db

# Restart all services
docker compose restart

# Restart specific service
docker compose restart jasmin-web

# Stop all services
docker compose down

# Start all services
docker compose up -d

# Check resource usage
docker stats
```

## 🗄️ Database Commands

```bash
# Run migrations
docker compose exec jasmin-web python manage.py migrate

# Create superuser
docker compose exec jasmin-web python manage.py createsuperuser

# Django shell
docker compose exec jasmin-web python manage.py shell

# Database backup
docker compose exec db pg_dump -U jasmin jasmin > backup_$(date +%Y%m%d).sql

# Restore database
cat backup.sql | docker compose exec -T db psql -U jasmin jasmin
```

## 📊 System Monitoring

```bash
# Check disk space
df -h

# Check memory
free -h

# Check CPU
top

# Check network
netstat -tulpn

# System info
htop
```

## 🔄 Update Application

```bash
cd jasmin-web-panel
git pull
docker compose pull
docker compose up -d
docker compose exec jasmin-web python manage.py migrate
docker compose exec jasmin-web python manage.py collectstatic --noinput
```

## 🛑 Emergency Commands

```bash
# Stop everything
docker compose down

# Remove all containers and volumes (DANGER!)
docker compose down -v

# Restart server
sudo reboot

# Check if ports are open
sudo netstat -tulpn | grep LISTEN
```

## 📁 Important Files

| File | Location | Purpose |
|------|----------|---------|
| Environment | `~/jasmin-web-panel/.env` | Configuration |
| Docker Compose | `~/jasmin-web-panel/docker-compose.yml` | Services |
| Logs | `~/jasmin-web-panel/logs/` | Application logs |
| Static Files | `~/jasmin-web-panel/public/static/` | Web assets |

## 🔐 Change Passwords

### Web Panel Admin
```bash
docker compose exec jasmin-web python manage.py changepassword admin
```

### Database Password
Edit `.env` file and update:
- `PRODB_URL`
- `POSTGRES_PASSWORD`
- `DB_PASS`

Then restart: `docker compose down && docker compose up -d`

## 🚨 Troubleshooting

### Service Won't Start
```bash
docker compose logs [service-name]
docker compose restart [service-name]
```

### Out of Disk Space
```bash
# Clean Docker
docker system prune -a

# Clean logs
cd logs && rm *.log
```

### High Memory Usage
```bash
# Check what's using memory
docker stats

# Restart services
docker compose restart
```

### Can't Access Web Panel
```bash
# Check if running
docker compose ps jasmin-web

# Check firewall
sudo ufw status

# Check if port is listening
sudo netstat -tulpn | grep 8999
```

## 💡 Pro Tips

1. **Always backup before updates**
   ```bash
   docker compose exec db pg_dump -U jasmin jasmin > backup.sql
   ```

2. **Monitor logs in real-time**
   ```bash
   docker compose logs -f --tail=100
   ```

3. **Check service health**
   ```bash
   docker compose ps
   ```

4. **Save costs - stop when not in use**
   ```bash
   # From AWS Console: Stop instance
   # You only pay for storage, not compute
   ```

5. **Set up billing alerts**
   - Go to AWS Billing Dashboard
   - Create budget alerts for $5, $10, $20

## 📞 Quick Help

- **Logs location:** `~/jasmin-web-panel/logs/`
- **Config file:** `~/jasmin-web-panel/.env`
- **Documentation:** http://docs.jasminsms.com
- **Community:** https://t.me/jasminwebpanel

---

**Instance IP:** 16.16.92.247  
**Instance Type:** t3.small (2 vCPU, 2 GB RAM)  
**Region:** EU North 1 (Stockholm)  
**OS:** Ubuntu 24.04 LTS
