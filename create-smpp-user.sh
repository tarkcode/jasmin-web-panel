#!/bin/bash

# Quick script to create SMPP user for provider connection

set -e

EC2_IP="16.16.92.247"
KEY_FILE="jasmin-web-key.pem"
EC2_USER="ubuntu"

echo "========================================="
echo "Create SMPP User for Provider"
echo "========================================="
echo ""

# Prompt for username
read -p "Enter username for SMS provider (e.g., sms_provider): " USERNAME
if [ -z "$USERNAME" ]; then
    echo "Error: Username cannot be empty"
    exit 1
fi

# Generate strong password
PASSWORD=$(openssl rand -base64 24)
echo ""
echo "Generated strong password: $PASSWORD"
echo ""
read -p "Press Enter to use this password, or type a custom password: " CUSTOM_PASSWORD

if [ ! -z "$CUSTOM_PASSWORD" ]; then
    PASSWORD="$CUSTOM_PASSWORD"
fi

echo ""
echo "Creating user in Jasmin..."

# Create user via jCli
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_IP" << EOF
cd jasmin-web-panel

# Create group and user
docker compose exec -T jasmin /bin/bash -c "
(
echo 'jcliadmin'
echo 'jclipwd'
sleep 1
echo 'group -a'
sleep 0.5
echo 'provider_group'
sleep 0.5
echo 'yes'
sleep 1
echo 'user -a'
sleep 0.5
echo '$USERNAME'
sleep 0.5
echo '$PASSWORD'
sleep 0.5
echo 'provider_group'
sleep 0.5
echo '$USERNAME'
sleep 1
echo 'persist'
sleep 1
echo 'quit'
) | telnet localhost 8990
"
EOF

echo ""
echo "========================================="
echo "✅ User Created Successfully!"
echo "========================================="
echo ""
echo "Provide this information to your SMS provider:"
echo ""
echo "SMPP Connection Details:"
echo "------------------------"
echo "Host: $EC2_IP"
echo "Port: 2775"
echo "Protocol: SMPP v3.4"
echo ""
echo "Credentials:"
echo "------------"
echo "System ID: $USERNAME"
echo "Password: $PASSWORD"
echo "System Type: (leave empty)"
echo ""
echo "⚠️  IMPORTANT: Save these credentials securely!"
echo ""
echo "You can also view users anytime by running:"
echo "  telnet $EC2_IP 8990"
echo "  Login: jcliadmin / jclipwd"
echo "  Command: user -l"
echo ""
