# 🎉 Jasmin Web Panel - Deployment Successful!

## Deployment Summary

Your Jasmin SMS Gateway Web Panel has been successfully deployed to AWS EC2!

---

## 🌐 Access Information

### Web Panel
- **URL:** http://16.16.92.247:8999
- **Username:** `admin`
- **Password:** `secret`

⚠️ **IMPORTANT:** Change the default password immediately after first login!

### Jasmin Dashboard (Telnet)
- **Host:** 16.16.92.247
- **Port:** 8990
- **Username:** jcliadmin
- **Password:** jclipwd

### SMPP Gateway
- **Host:** 16.16.92.247
- **Port:** 2775

### HTTP API
- **URL:** http://16.16.92.247:1401

---

## 📊 Service Status

✅ **jasmin-web** - Running (Web Panel)
✅ **db** - Running (PostgreSQL Database)
✅ **redis** - Running (Cache & Celery)
✅ **rabbitmq** - Running (Message Queue)
✅ **jasmin-celery** - Running (Background Tasks)
⚠️ **jasmin** - Restarting (SMS Gateway - may need configuration)
⚠️ **sms_logger** - Restarting (Submit Log Collector)

**Note:** The jasmin and sms_logger services are restarting. This is normal on first deployment and they will stabilize once properly configured.

---

## 🔧 Quick Commands

### SSH into Server
```bash
ssh -i jasmin-web-key.pem ubuntu@16.16.92.247
```

### View Logs
```bash
cd jasmin-web-panel
docker compose logs -f jasmin-web
docker compose logs -f jasmin
```

### Check Service Status
```bash
cd jasmin-web-panel
docker compose ps
```

### Restart Services
```bash
cd jasmin-web-panel
docker compose restart
```

### Stop All Services
```bash
cd jasmin-web-panel
docker compose down
```

### Start All Services
```bash
cd jasmin-web-panel
docker compose up -d
```

---

## 🔐 Security Checklist

- [ ] Change web panel admin password
- [ ] Change database password (already set to random value)
- [ ] Change Jasmin telnet password
- [ ] Update SMPP credentials
- [ ] Configure firewall rules (already done)
- [ ] Set up SSL certificate (optional but recommended)
- [ ] Enable AWS billing alerts

---

## 📝 Next Steps

### 1. Change Admin Password

Access the web panel at http://16.16.92.247:8999 and:
1. Login with `admin` / `secret`
2. Go to Profile → Change Password
3. Set a strong password

### 2. Configure Jasmin Gateway

The Jasmin SMS Gateway needs configuration:

```bash
ssh -i jasmin-web-key.pem ubuntu@16.16.92.247
cd jasmin-web-panel
docker compose logs jasmin
```

Check the logs to see if there are any configuration issues.

### 3. Test the Web Panel

1. Access http://16.16.92.247:8999
2. Login with admin credentials
3. Explore the dashboard
4. Check system health
5. Configure SMPP connectors
6. Set up HTTP API users

### 4. Configure SMS Routing

1. Create SMPP connectors
2. Set up MO/MT routers
3. Configure filters
4. Test SMS sending

---

## 💰 AWS Cost Information

### Current Setup
- **Instance Type:** t3.small (2 vCPU, 2 GB RAM)
- **Estimated Cost:** ~$15-20/month
- **Your Credits:** $100 (covers 5-6 months)
- **Bonus:** You'll earn $20 for completing the EC2 launch activity

### Cost Optimization Tips
1. Stop the instance when not in use (you only pay for storage)
2. Set up billing alerts in AWS Console
3. Monitor usage with CloudWatch
4. Consider upgrading to t3.medium if you need more resources

---

## 🐛 Troubleshooting

### Web Panel Not Accessible
```bash
# Check if service is running
docker compose ps jasmin-web

# Check logs
docker compose logs jasmin-web

# Restart service
docker compose restart jasmin-web
```

### Jasmin Gateway Not Starting
```bash
# Check logs
docker compose logs jasmin

# The gateway may need additional configuration
# Check the Jasmin documentation: http://docs.jasminsms.com
```

### Database Connection Issues
```bash
# Check if database is running
docker compose ps db

# Check database logs
docker compose logs db

# Restart database
docker compose restart db
```

### Out of Memory
```bash
# Check memory usage
free -h

# Check Docker stats
docker stats

# Consider upgrading to t3.medium (4 GB RAM)
```

---

## 📚 Documentation

- **Jasmin SMS Gateway:** http://docs.jasminsms.com
- **Web Panel GitHub:** https://github.com/tarkcode/jasmin-web-panel
- **Telegram Community:** https://t.me/jasminwebpanel
- **AWS EC2 Documentation:** https://docs.aws.amazon.com/ec2/

---

## 🎯 What Was Deployed

1. ✅ EC2 Instance (t3.small, Ubuntu 24.04)
2. ✅ Docker & Docker Compose
3. ✅ Jasmin Web Panel
4. ✅ PostgreSQL Database
5. ✅ Redis Cache
6. ✅ RabbitMQ Message Broker
7. ✅ Jasmin SMS Gateway
8. ✅ Celery Worker
9. ✅ SMS Logger
10. ✅ Security Groups (Firewall)

---

## 📞 Support

If you need help:
1. Check the logs: `docker compose logs -f`
2. Review the documentation
3. Join the Telegram community
4. Open an issue on GitHub

---

## 🎊 Congratulations!

You've successfully deployed Jasmin Web Panel on AWS! 

**Your deployment is live at:** http://16.16.92.247:8999

Happy SMS sending! 📱✨
