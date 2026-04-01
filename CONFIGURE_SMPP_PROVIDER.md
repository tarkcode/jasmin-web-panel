# Configure SMPP Provider Connection

## Server Information for Your SMS Provider

### Connection Details
```
Public IP: 16.16.92.247
SMPP Port: 2775
Protocol: SMPP v3.4
```

**Full Endpoint:** `16.16.92.247:2775`

---

## Step-by-Step Configuration

### Step 1: Create a User for Your SMS Provider

#### Via Telnet (jCli)

```bash
# Connect to Jasmin
telnet 16.16.92.247 8990

# Login
Username: jcliadmin
Password: jclipwd

# Create a group first
group -a
> gid: provider_group
> enabled: yes
ok

# Create a user
user -a
> username: sms_provider
> password: YOUR_STRONG_PASSWORD
> gid: provider_group
> uid: sms_provider
ok

# List users to verify
user -l

# Exit
quit
```

#### Via SSH (Automated)

```bash
ssh -i jasmin-web-key.pem ubuntu@16.16.92.247

cd jasmin-web-panel

# Create user via jCli commands
docker compose exec jasmin /bin/bash -c "
echo 'group -a
gid provider_group
enabled yes

user -a  
username sms_provider
password YOUR_STRONG_PASSWORD
gid provider_group
uid sms_provider

persist
' | telnet localhost 8990
"
```

---

### Step 2: Configure SMPP Connector (Optional - for outbound)

If you need to connect TO your provider's SMPP server (for sending SMS):

```bash
telnet 16.16.92.247 8990
# Login: jcliadmin / jclipwd

# Add SMPP connector
smppccm -a
> cid: provider_connector
> host: PROVIDER_IP
> port: PROVIDER_PORT
> username: YOUR_USERNAME_FROM_PROVIDER
> password: YOUR_PASSWORD_FROM_PROVIDER
> submit_throughput: 10
ok

# Start the connector
smppccm -1 provider_connector

# Check status
smppccm -l

# Exit
quit
```

---

### Step 3: Configure MT Router (Message Routing)

Create a route to send messages through your provider:

```bash
telnet 16.16.92.247 8990
# Login: jcliadmin / jclipwd

# Create a default route
mtrouter -a
> type: DefaultRoute
> connector: smppc(provider_connector)
> rate: 0.0
ok

# List routes
mtrouter -l

# Persist configuration
persist

# Exit
quit
```

---

## Information to Provide Your SMS Provider

### For Inbound Connections (Provider connects to you)

Send them this information:

```
SMPP Server Details:
--------------------
Host: 16.16.92.247
Port: 2775
Protocol: SMPP v3.4

Credentials:
-----------
System ID: sms_provider
Password: [YOUR_STRONG_PASSWORD]
System Type: (leave empty or "SMPP")

Connection Settings:
-------------------
Bind Type: Transceiver (or Transmitter/Receiver)
Interface Version: 3.4
Address TON: 1 (International)
Address NPI: 1 (ISDN)
```

### For Outbound Connections (You connect to provider)

You need from them:

```
SMPP Server Details:
--------------------
Host: [PROVIDER_IP]
Port: [PROVIDER_PORT]
Protocol: SMPP v3.4

Credentials:
-----------
System ID: [PROVIDED_BY_THEM]
Password: [PROVIDED_BY_THEM]
System Type: [PROVIDED_BY_THEM]

Additional Settings:
-------------------
Throughput Limit: [MESSAGES_PER_SECOND]
Source Address: [YOUR_SENDER_ID]
```

---

## Testing the Connection

### Test 1: Check if SMPP Port is Open

From your local machine:
```bash
telnet 16.16.92.247 2775
```

You should see a connection (may show binary data). Press Ctrl+] then type `quit`.

### Test 2: Check Jasmin SMPP Server Status

```bash
ssh -i jasmin-web-key.pem ubuntu@16.16.92.247
cd jasmin-web-panel
docker compose logs jasmin | grep "SMPPServer Started"
```

Should show: `SMPPServer Started`

### Test 3: Monitor Connections

```bash
# Via telnet
telnet 16.16.92.247 8990
# Login: jcliadmin / jclipwd

# Check SMPP server stats
stats --smpps

# Check user stats
stats --users

# Exit
quit
```

### Test 4: Send Test SMS via HTTP API

```bash
curl -X POST http://16.16.92.247:1401/send \
  -d "username=sms_provider" \
  -d "password=YOUR_PASSWORD" \
  -d "to=+1234567890" \
  -d "content=Test message from Jasmin"
```

---

## Security Considerations

### 1. Restrict SMPP Access (Recommended)

If you know your provider's IP address, restrict port 2775 to only their IP:

```bash
# SSH into server
ssh -i jasmin-web-key.pem ubuntu@16.16.92.247

# Add firewall rule (replace PROVIDER_IP with actual IP)
sudo ufw allow from PROVIDER_IP to any port 2775 proto tcp

# Remove the open rule
sudo ufw delete allow 2775/tcp

# Check rules
sudo ufw status numbered
```

### 2. Use Strong Passwords

Generate a strong password:
```bash
openssl rand -base64 32
```

### 3. Enable TLS (Optional)

For secure SMPP connections, you can configure TLS in jasmin.cfg:
```ini
[smpp-server]
bind = 0.0.0.0
port = 2775
ssl = yes
ssl_cert = /path/to/cert.pem
ssl_key = /path/to/key.pem
```

---

## Monitoring & Logs

### View SMPP Connection Logs

```bash
ssh -i jasmin-web-key.pem ubuntu@16.16.92.247
cd jasmin-web-panel

# Real-time logs
docker compose logs -f jasmin

# Filter for SMPP connections
docker compose logs jasmin | grep SMPP

# Check for bind requests
docker compose logs jasmin | grep "bind_"
```

### View Submit Logs (SMS Messages)

Access the web panel:
1. Go to http://16.16.92.247:8999
2. Navigate to **Submit Logs**
3. View all SMS messages sent/received

---

## Troubleshooting

### Provider Can't Connect

1. **Check if port is open:**
   ```bash
   sudo netstat -tulpn | grep 2775
   ```

2. **Check AWS Security Group:**
   - Go to AWS EC2 Console
   - Select your instance
   - Check Security Groups
   - Ensure port 2775 is open (0.0.0.0/0 or provider's IP)

3. **Check Jasmin logs:**
   ```bash
   docker compose logs jasmin -f
   ```

4. **Test from provider's network:**
   Ask them to run:
   ```bash
   telnet 16.16.92.247 2775
   ```

### Authentication Failures

1. **Verify user exists:**
   ```bash
   telnet 16.16.92.247 8990
   # Login: jcliadmin / jclipwd
   user -l
   ```

2. **Check credentials match**

3. **View authentication logs:**
   ```bash
   docker compose logs jasmin | grep "authentication"
   ```

### Messages Not Routing

1. **Check MT Router:**
   ```bash
   telnet 16.16.92.247 8990
   # Login: jcliadmin / jclipwd
   mtrouter -l
   ```

2. **Check connector status:**
   ```bash
   smppccm -l
   ```

3. **View routing logs:**
   ```bash
   docker compose logs jasmin | grep "route"
   ```

---

## Quick Reference Commands

```bash
# SSH to server
ssh -i jasmin-web-key.pem ubuntu@16.16.92.247

# Access Jasmin CLI
telnet 16.16.92.247 8990
# Login: jcliadmin / jclipwd

# Common jCli commands
user -l              # List users
group -l             # List groups
smppccm -l           # List SMPP connectors
mtrouter -l          # List MT routes
morouter -l          # List MO routes
filter -l            # List filters
stats --help         # View statistics options
persist              # Save configuration
quit                 # Exit

# View logs
cd jasmin-web-panel
docker compose logs -f jasmin
docker compose logs -f sms_logger
```

---

## Support Resources

- **Jasmin Documentation:** http://docs.jasminsms.com
- **SMPP Configuration:** http://docs.jasminsms.com/en/latest/routing/index.html
- **jCli Reference:** http://docs.jasminsms.com/en/latest/management/jcli/index.html
- **Telegram Community:** https://t.me/jasminwebpanel

---

**Server IP:** 16.16.92.247  
**SMPP Port:** 2775  
**Status:** ✅ Ready for provider connections
