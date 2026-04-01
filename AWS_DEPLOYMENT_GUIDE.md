# Jasmin Web Panel - AWS Deployment Guide

## Instance Information
- **Public IP:** 16.16.92.247
- **Instance Type:** t3.small (2 vCPU, 2 GB RAM)
- **OS:** Ubuntu Server 24.04 LTS
- **Region:** EU North 1 (Stockholm)

## Quick Start

### Option 1: Automated Deployment (Recommended)

Run the deployment script from your local machine:

```bash
chmod +x deploy-to-aws.sh
./deploy-to-aws.sh
```

This will automatically:
- Set up SSH connection
- Install Docker & Docker Compose
- Install Git
- Clone your repository
- Create environment file

### Option 2: Manual Deployment

#### Step 1: Connect to EC2 Instance

```bash
chmod 400 jasmin-web-key.pem
ssh -i jasmin-web-key.pem ubuntu@16.16.92.247
```

#### Step 2: Update System

```bash
sudo apt update && sudo apt upgrade -y
```

#### Step 3: Install Docker & Docker Compose

```bash
# Install Docker
sudo apt install -y docker.io docker-compose-v2

# Enable and start Docker
sudo systemctl enable docker
sudo systemctl start docker

# Add user to docker group
sudo usermod -aG docker ubuntu

# Log out and back in for group changes to take effect
exit
```

Reconnect:
```bash
ssh -i jasmin-web-key.pem ubuntu@16.16.92.247
```

#### Step 4: Install Git

```bash
sudo apt install -y git curl
```

#### Step 5: Clone Repository

```bash
git clone https://github.com/tarkcode/jasmin-web-panel.git
cd jasmin-web-panel
```

#### Step 6: Configure Environment

```bash
# Copy sample environment file
cp sample.env .env

# Edit environment file
nano .env
```

**Important environment variables to configure:**

```ini
DEBUG=False
SECRET_KEY=CHANGE_THIS_TO_A_LONG_RANDOM_STRING
ALLOWED_HOSTS=16.16.92.247,ec2-16-16-92-247.eu-north-1.compute.amazonaws.com
CSRF_TRUSTED_ORIGINS=http://16.16.92.247:8999,http://ec2-16-16-92-247.eu-north-1.compute.amazonaws.com:8999

# Database (Docker will create this)
PRODB_URL=postgres://jasmin:CHANGE_THIS_PASSWORD@db:5432/jasmin
POSTGRES_DB=jasmin
POSTGRES_USER=jasmin
POSTGRES_PASSWORD=CHANGE_THIS_PASSWORD

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Jasmin Gateway
TELNET_HOST=jasmin
TELNET_PORT=8990
TELNET_USERNAME=jcliadmin
TELNET_PW=jclipwd

# Enable submit logging
SUBMIT_LOG=True

# Ports
JASMIN_WEB_PORT=8999
JASMIN_SMS_PORT=2775
JASMIN_DASHBOARD_PORT=8990
JASMIN_HTTP_API_PORT=1401
```

**Generate a secure SECRET_KEY:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

#### Step 7: Start Services

```bash
# Start all services
docker compose up -d

# Check if services are running
docker compose ps

# View logs
docker compose logs -f jasmin-web
```

#### Step 8: Initialize Database

```bash
# Run migrations
docker compose exec jasmin-web python manage.py migrate

# Create superuser
docker compose exec jasmin-web python manage.py createsuperuser

# Collect static files
docker compose exec jasmin-web python manage.py collectstatic --noinput
```

## Access the Application

### Web Panel
- URL: http://16.16.92.247:8999
- Default Username: `admin`
- Default Password: `secret`

**⚠️ IMPORTANT: Change the default password immediately after first login!**

### Jasmin Dashboard (Telnet)
- Host: 16.16.92.247
- Port: 8990
- Username: jcliadmin
- Password: jclipwd

### SMPP Gateway
- Host: 16.16.92.247
- Port: 2775

### HTTP API
- URL: http://16.16.92.247:1401

## Useful Commands

### Check Service Status
```bash
docker compose ps
```

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f jasmin-web
docker compose logs -f jasmin
docker compose logs -f db
```

### Restart Services
```bash
# Restart all
docker compose restart

# Restart specific service
docker compose restart jasmin-web
```

### Stop Services
```bash
docker compose down
```

### Update Application
```bash
cd jasmin-web-panel
git pull
docker compose pull
docker compose up -d
docker compose exec jasmin-web python manage.py migrate
```

### Database Backup
```bash
docker compose exec db pg_dump -U jasmin jasmin > backup_$(date +%Y%m%d).sql
```

### Monitor Resources
```bash
# Docker stats
docker stats

# System resources
htop
```

## Troubleshooting

### Cannot connect to instance
- Wait 2-3 minutes after launch for status checks to complete
- Check security group allows SSH (port 22) from your IP
- Verify key file permissions: `chmod 400 jasmin-web-key.pem`

### Services not starting
```bash
# Check logs
docker compose logs

# Check disk space
df -h

# Check memory
free -h
```

### Web panel not accessible
- Verify security group allows port 8999
- Check if service is running: `docker compose ps`
- Check logs: `docker compose logs jasmin-web`

### Database connection errors
- Check if PostgreSQL is running: `docker compose ps db`
- Verify PRODB_URL in .env matches POSTGRES_* variables
- Check logs: `docker compose logs db`

## Security Recommendations

1. **Change default passwords immediately**
   - Web panel admin password
   - Database password
   - Jasmin telnet password

2. **Restrict security group access**
   - Limit SSH (22) to your IP only
   - Consider using VPN for sensitive ports

3. **Enable HTTPS**
   - Set up Nginx reverse proxy
   - Use Let's Encrypt for SSL certificate

4. **Regular backups**
   - Set up automated database backups
   - Store backups in S3

5. **Monitor costs**
   - Set up AWS billing alerts
   - Monitor instance usage

## Cost Optimization

- **Stop instance when not in use:** You only pay for storage, not compute
- **Use Elastic IP carefully:** Free when attached to running instance
- **Monitor with CloudWatch:** Set up alarms for unusual activity
- **t3.small cost:** ~$15-20/month (covered by your $100 credit for 5-6 months)

## Support

- **GitHub Repository:** https://github.com/tarkcode/jasmin-web-panel
- **Jasmin Documentation:** http://docs.jasminsms.com
- **Telegram Community:** https://t.me/jasminwebpanel

## Next Steps

1. ✅ Connect to EC2 instance
2. ✅ Install Docker & dependencies
3. ✅ Clone repository
4. ✅ Configure environment
5. ✅ Start services
6. ✅ Initialize database
7. ✅ Access web panel
8. ✅ Change default passwords
9. ✅ Configure Jasmin gateway
10. ✅ Test SMS sending

Good luck with your deployment! 🚀
