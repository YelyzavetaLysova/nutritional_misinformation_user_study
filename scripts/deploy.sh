#!/bin/zsh
# Deployment script for nutritional_misinformation_user_study

echo "Starting deployment to server at 10.1.1.140..."

# Ensure we're in the right directory
cd "$(dirname "$0")" || exit
cd ..

# Check if the SSH key file exists
SSH_KEY_FILE="$HOME/.ssh/nrec_key"
if [[ ! -f "$SSH_KEY_FILE" ]]; then
  echo "Creating SSH key file at $SSH_KEY_FILE..."
  cat > "$SSH_KEY_FILE" << 'EOF'
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA2rnn1BiAR9FcrU51f5JKlEW6M4OdfAN2IWl8yrPbjm0tZvgl
h2EuyJct9W0sQhzLotcU4H3e8/ryZ89G9Ll8wJ0zGLoZk1dUJhmclgpvfvLlu+WW
be+ExBCOocYSZZRMN0HSEK6Sqsjue1b6MsjUVSKansVibwhjaLmRSvW7tT9E/9WJ
sMe+JdAfS7A4UQziwa8o71dfyX2gM7BxKhiCTiXR7nQD/hZnk+W6nrOc74N2RDYH
rb8FqfLqYp8Os4z/4uc36aTre9rSX6tOW4fSVliQ8z1cOJYKJKuwm8A/Zj9G1Sq+
PYVBNxdUgQnadbXNap7HSDYQM5JQiaMmudVJZQIDAQABAoIBAFKm34jRPWBmJ+xB
crsjT9VZx/QBbzhWooQbtZFvh675aKe5a40N1zzri+1rNMdC1FyThAsU5XQyxvkd
ZYXCtfafMJjOci2wWVcQZJB6HwnMxa1MI50lXnksfIl7LKZ/9JEI6VVucnPg++VV
x7P7GemV6vHGSt0EQXRocxPtaeIh9D3qLGcTGK/k5gDIKoDTVbjTSWDhqyL04ec+
izkfqp+I9UVaDea7b/bHl5OwdsYiRmKGHVeHnmfbABQF4FKm0x08L95MNUm1fkvA
LFsoWB048yxNV4Vkos7xa45QzOuIsLCoBRE3CvmylntsMVokUbnM4ngI5TkvqIj2
askeqoECgYEA/Gxwu96xP8S6C/YXH+t05wAN5kW61JnvIMbXSjMVYZm+mk3gLaqd
IoXlOEvlyMu9xKBTaKSlWsU+qUKcsYh1G7ZdyFjpVywL2qcuUmvwbKWmkeazB2lW
Hjsw1dmwttAi3NwZDlt/1Up1XNQA6xRS7/ZR+W/W9BRMOcb3xTC9i8UCgYEA3dM9
/Ci/5urK37M6aQ6LsUIROLjzDNLmyQVqFGerXl
07+aeCdVVC/A0p0hpupQV7EboviAxFUCP/N4jwMqIXq/+6d7IXknYxZd8EPE5ayb
qPxOtcvjmKgTkGOCOrmv51uw76vm4EmXNz2YgSECgYEAnniV7dxI+vfOtWOx8OAp
bDykfUSZno9liPZMgtC/Q576AnWRoBnUvK/C0C0V/ZGreZ4Nv0xeYzYhuLGRHgPF
Qbij9/uZwphseMEsW6JYNl1ozYBANQ70edY/OoKIZr0UpgOn11OqVYWBWN3gFbWU
vAGwRSDpmiKEGGHJe4q19OECgYB5kcTfLIwoshzysEcSKzJ8YxxilDEOwlpPuPBU
yMDsDLRMKAMfIYQRxLAeajcskxR6OegsBU0V3pCgI8+sXZtMzAueE51O0pxXfTNP
cxK2ZgiX8pr2w1HzBV/1qRNwkuN87/0bPrOwZH5mcm7Oagq8PnnN9O1iXLaaYxpx
lttWoQKBgQD13hAqsgQAXXgO2jRbQ3X0LptPPu8tjNRS5F1IN2C3dAOxG7NU5LLD
J38d+w1V4u9d9t4sigYjemQF5G4IeQ2S++PC8Gl5bUhhVyH/Byn/p2beWNgqvnUr
gg4cx5jRCi5yYE5CzzBvnQVhyzBLlPmo0KxmOozYsMZ15SuvDDf5sw==
-----END RSA PRIVATE KEY-----
EOF
  chmod 600 "$SSH_KEY_FILE"
  echo "SSH key file created."
fi

# Add the server to known_hosts if it's not already there
if ! ssh-keygen -F 10.1.1.140 > /dev/null; then
  echo "Adding server to known_hosts..."
  ssh-keyscan -H 10.1.1.140 >> ~/.ssh/known_hosts
fi

# Test SSH connection
echo "Testing SSH connection..."
if ! ssh -i "$SSH_KEY_FILE" ubuntu@10.1.1.140 "echo 'SSH connection successful'"; then
  echo "SSH connection failed. Please check your SSH key and server configuration."
  exit 1
fi

# Deploy using rsync
echo "Deploying application files..."
rsync -avz --exclude 'venv' --exclude '.git' --exclude '__pycache__' --exclude 'logs/*.log' \
  --exclude 'data/responses/*.json' --exclude 'data/responses/*.csv' \
  -e "ssh -i $SSH_KEY_FILE" \
  ./ ubuntu@10.1.1.140:~/nutritional_misinformation_user_study/

# Run the remote setup script
echo "Setting up application on the server..."
ssh -i "$SSH_KEY_FILE" ubuntu@10.1.1.140 'bash -s' << 'EOF'
  cd ~/nutritional_misinformation_user_study
  
  # Create Python virtual environment if it doesn't exist
  if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
  fi
  
  # Activate virtual environment and install requirements
  echo "Installing dependencies..."
  source venv/bin/activate
  pip install -r requirements.txt
  
  # Create necessary directories
  echo "Creating directories..."
  mkdir -p data/responses logs
  chmod -R 755 data logs
  
  # Create systemd service file if it doesn't exist
  if [ ! -f /etc/systemd/system/nutritional-survey.service ]; then
    echo "Creating systemd service..."
    sudo bash -c 'cat > /etc/systemd/system/nutritional-survey.service << EOT
[Unit]
Description=Nutritional Misinformation Survey
After=network.target

[Service]
User=$(whoami)
Group=$(whoami)
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8000 run:app
Restart=always

[Install]
WantedBy=multi-user.target
EOT'
  fi
  
  # Create nginx config if it doesn't exist
  if [ ! -f /etc/nginx/sites-available/nutritional-survey ]; then
    echo "Creating Nginx configuration..."
    sudo bash -c 'cat > /etc/nginx/sites-available/nutritional-survey << EOT
server {
    listen 80;
    server_name 10.1.1.140;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOT'
    
    # Enable the site
    sudo ln -sf /etc/nginx/sites-available/nutritional-survey /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # Check Nginx configuration
    sudo nginx -t && sudo systemctl restart nginx
  fi
  
  # Start the service
  echo "Starting the application..."
  sudo systemctl daemon-reload
  sudo systemctl enable nutritional-survey
  sudo systemctl restart nutritional-survey
  
  # Display status
  echo "Service status:"
  sudo systemctl status nutritional-survey --no-pager
  
  echo "Deployment completed successfully."
EOF

echo "Deployment script finished."
