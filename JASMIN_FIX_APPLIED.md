# Jasmin Connection Fix Applied ✅

## Issue
The Jasmin SMS Gateway was showing "Cannot connect, service not started or telnet not configured" in the web panel.

## Root Cause
The Jasmin container was missing:
1. Configuration file (`jasmin.cfg`)
2. AMQP specification file (`amqp0-9-1.xml`)

## Fix Applied

### 1. Created Jasmin Configuration File
Created `/jasmin_config/jasmin.cfg` with proper settings:
```ini
[sm-listener]
publish_submit_sm_resp = True

[jcli]
bind = 0.0.0.0
port = 8990

[redis-client]
host = redis
port = 6379

[amqp-broker]
host = rabbitmq
port = 5672

[smpp-server]
bind = 0.0.0.0
port = 2775

[http-api]
bind = 0.0.0.0
port = 1401
```

### 2. Downloaded AMQP Spec File
Downloaded `amqp0-9-1.xml` from Jasmin repository to `/jasmin_config/resource/`

### 3. Restarted Services
Restarted Jasmin and SMS Logger services to apply changes.

## Current Status

All Jasmin services are now running:
- ✅ **SMPP Server** - Port 2775
- ✅ **HTTP API** - Port 1401  
- ✅ **jCli (Telnet)** - Port 8990
- ✅ **AMQP Broker** - Connected to RabbitMQ
- ✅ **Redis Client** - Connected to Redis
- ✅ **Router** - Active
- ✅ **DLR Lookup** - Active
- ✅ **SMS Logger** - Active

## Verification

### Check Jasmin Status
```bash
ssh -i jasmin-web-key.pem ubuntu@16.16.92.247
cd jasmin-web-panel
docker compose ps
docker compose logs jasmin --tail=20
```

### Test Telnet Connection
```bash
telnet 16.16.92.247 8990
# Username: jcliadmin
# Password: jclipwd
```

### Access Web Panel
1. Go to: http://16.16.92.247:8999
2. Login with: admin / secret
3. The "Jasmin SMS Gateway" box should now show "Connected" status

## Next Steps

1. **Refresh the web panel** - The dashboard should now show Jasmin as connected
2. **Configure SMPP Connectors** - Add your SMPP provider connections
3. **Set up Users** - Create users for sending SMS
4. **Configure Routers** - Set up MT/MO routing rules
5. **Test SMS Sending** - Send a test SMS through the HTTP API or SMPP

## Testing Jasmin

### Via Telnet (jCli)
```bash
telnet 16.16.92.247 8990
# Login: jcliadmin / jclipwd
# Commands:
stats --help
user -l
group -l
```

### Via HTTP API
```bash
# Send SMS (after configuring user and route)
curl -X POST http://16.16.92.247:1401/send \
  -d "username=YOUR_USER" \
  -d "password=YOUR_PASS" \
  -d "to=+1234567890" \
  -d "content=Test message"
```

## Files Modified/Created

1. `/home/ubuntu/jasmin-web-panel/jasmin_config/jasmin.cfg` - Created
2. `/home/ubuntu/jasmin-web-panel/jasmin_config/resource/amqp0-9-1.xml` - Downloaded

## Troubleshooting

If Jasmin still shows as disconnected:

1. **Check logs:**
   ```bash
   docker compose logs jasmin -f
   ```

2. **Verify telnet port is accessible:**
   ```bash
   telnet 16.16.92.247 8990
   ```

3. **Check environment variables in web panel:**
   ```bash
   cat .env | grep TELNET
   ```
   Should show:
   ```
   TELNET_HOST=jasmin
   TELNET_PORT=8990
   TELNET_USERNAME=jcliadmin
   TELNET_PW=jclipwd
   ```

4. **Restart web panel:**
   ```bash
   docker compose restart jasmin-web
   ```

## Documentation

- **Jasmin Documentation:** http://docs.jasminsms.com
- **jCli Commands:** http://docs.jasminsms.com/en/latest/management/jcli/index.html
- **HTTP API:** http://docs.jasminsms.com/en/latest/apis/ja-http/index.html
- **SMPP Configuration:** http://docs.jasminsms.com/en/latest/routing/index.html

---

**Fix applied on:** 2026-04-01 06:11 UTC  
**Status:** ✅ Jasmin SMS Gateway is now running and accessible
