#!/bin/bash

# Jasmin Web Panel - AWS Deployment Script
# This script will deploy the complete Jasmin SMS Gateway + Web Panel on AWS EC2

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Jasmin Web Panel - AWS Deployment${NC}"
echo -e "${GREEN}========================================${NC}"

# Configuration
EC2_IP="16.16.92.247"
KEY_FILE="jasmin-web-key.pem"
EC2_USER="ubuntu"

# Check if key file exists
if [ ! -f "$KEY_FILE" ]; then
    echo -e "${RED}Error: Key file $KEY_FILE not found!${NC}"
    exit 1
fi

# Set correct permissions for key file
chmod 400 "$KEY_FILE"
echo -e "${GREEN}✓ Key file permissions set${NC}"

# Function to run commands on EC2
run_remote() {
    ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_IP" "$@"
}

# Function to copy files to EC2
copy_to_ec2() {
    scp -i "$KEY_FILE" -o StrictHostKeyChecking=no "$1" "$EC2_USER@$EC2_IP:$2"
}

echo -e "\n${YELLOW}Step 1: Testing SSH connection...${NC}"
if run_remote "echo 'SSH connection successful'"; then
    echo -e "${GREEN}✓ SSH connection established${NC}"
else
    echo -e "${RED}✗ SSH connection failed. Please wait a minute and try again.${NC}"
    exit 1
fi

echo -e "\n${YELLOW}Step 2: Updating system packages...${NC}"
run_remote "sudo apt update && sudo apt upgrade -y"
echo -e "${GREEN}✓ System updated${NC}"

echo -e "\n${YELLOW}Step 3: Installing Docker...${NC}"
run_remote "sudo apt install -y docker.io docker-compose-v2"
run_remote "sudo systemctl enable docker"
run_remote "sudo systemctl start docker"
run_remote "sudo usermod -aG docker ubuntu"
echo -e "${GREEN}✓ Docker installed${NC}"

echo -e "\n${YELLOW}Step 4: Installing Git...${NC}"
run_remote "sudo apt install -y git curl"
echo -e "${GREEN}✓ Git installed${NC}"

echo -e "\n${YELLOW}Step 5: Cloning repository...${NC}"
run_remote "git clone https://github.com/tarkcode/jasmin-web-panel.git"
echo -e "${GREEN}✓ Repository cloned${NC}"

echo -e "\n${YELLOW}Step 6: Creating environment file...${NC}"
run_remote "cd jasmin-web-panel && cp sample.env .env"
echo -e "${GREEN}✓ Environment file created${NC}"

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Initial Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "\n${YELLOW}Next steps:${NC}"
echo -e "1. SSH into the server: ${GREEN}ssh -i $KEY_FILE $EC2_USER@$EC2_IP${NC}"
echo -e "2. Edit the .env file: ${GREEN}cd jasmin-web-panel && nano .env${NC}"
echo -e "3. Start the services: ${GREEN}docker compose up -d${NC}"
echo -e "4. Access the web panel: ${GREEN}http://$EC2_IP:8999${NC}"
echo -e "\n${YELLOW}Default credentials:${NC}"
echo -e "Username: ${GREEN}admin${NC}"
echo -e "Password: ${GREEN}secret${NC}"
echo -e "\n${RED}⚠️  Change the default password immediately after first login!${NC}"
