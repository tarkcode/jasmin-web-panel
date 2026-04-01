#!/bin/bash

# Jasmin Web Panel - Complete Deployment Script
# This script completes the deployment on AWS EC2

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

EC2_IP="16.16.92.247"
KEY_FILE="jasmin-web-key.pem"
EC2_USER="ubuntu"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Completing Jasmin Web Panel Deployment${NC}"
echo -e "${GREEN}========================================${NC}"

# Generate a secure SECRET_KEY
echo -e "\n${YELLOW}Generating secure SECRET_KEY...${NC}"
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
echo -e "${GREEN}✓ SECRET_KEY generated${NC}"

# Generate a secure database password
DB_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
echo -e "${GREEN}✓ Database password generated${NC}"

# Copy production.env to server
echo -e "\n${YELLOW}Copying production environment file...${NC}"
scp -i "$KEY_FILE" -o StrictHostKeyChecking=no production.env "$EC2_USER@$EC2_IP:~/jasmin-web-panel/.env"
echo -e "${GREEN}✓ Environment file copied${NC}"

# Update environment file with generated secrets
echo -e "\n${YELLOW}Configuring environment with secure credentials...${NC}"
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_IP" << EOF
cd jasmin-web-panel
sed -i "s/CHANGE_THIS_TO_A_LONG_RANDOM_STRING_MINIMUM_50_CHARACTERS/$SECRET_KEY/g" .env
sed -i "s/CHANGE_THIS_DB_PASSWORD/$DB_PASSWORD/g" .env
echo -e "${GREEN}✓ Environment configured${NC}"
EOF

# Start Docker services
echo -e "\n${YELLOW}Starting Docker services...${NC}"
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_IP" << 'EOF'
cd jasmin-web-panel
docker compose up -d
echo "Waiting for services to start..."
sleep 30
EOF
echo -e "${GREEN}✓ Services started${NC}"

# Run database migrations
echo -e "\n${YELLOW}Running database migrations...${NC}"
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_IP" << 'EOF'
cd jasmin-web-panel
docker compose exec -T jasmin-web python manage.py migrate
EOF
echo -e "${GREEN}✓ Database migrated${NC}"

# Collect static files
echo -e "\n${YELLOW}Collecting static files...${NC}"
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_IP" << 'EOF'
cd jasmin-web-panel
docker compose exec -T jasmin-web python manage.py collectstatic --noinput
EOF
echo -e "${GREEN}✓ Static files collected${NC}"

# Check service status
echo -e "\n${YELLOW}Checking service status...${NC}"
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_IP" << 'EOF'
cd jasmin-web-panel
docker compose ps
EOF

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete! 🎉${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "\n${YELLOW}Access Information:${NC}"
echo -e "Web Panel: ${GREEN}http://$EC2_IP:8999${NC}"
echo -e "Username: ${GREEN}admin${NC}"
echo -e "Password: ${GREEN}secret${NC}"
echo -e "\n${RED}⚠️  IMPORTANT: Change the default password immediately!${NC}"
echo -e "\n${YELLOW}Jasmin Dashboard (Telnet):${NC}"
echo -e "Host: ${GREEN}$EC2_IP${NC}"
echo -e "Port: ${GREEN}8990${NC}"
echo -e "Username: ${GREEN}jcliadmin${NC}"
echo -e "Password: ${GREEN}jclipwd${NC}"
echo -e "\n${YELLOW}SMPP Gateway:${NC}"
echo -e "Host: ${GREEN}$EC2_IP${NC}"
echo -e "Port: ${GREEN}2775${NC}"
echo -e "\n${YELLOW}HTTP API:${NC}"
echo -e "URL: ${GREEN}http://$EC2_IP:1401${NC}"
echo -e "\n${YELLOW}Useful Commands:${NC}"
echo -e "SSH: ${GREEN}ssh -i $KEY_FILE $EC2_USER@$EC2_IP${NC}"
echo -e "View logs: ${GREEN}docker compose logs -f${NC}"
echo -e "Restart: ${GREEN}docker compose restart${NC}"
echo -e "Stop: ${GREEN}docker compose down${NC}"
