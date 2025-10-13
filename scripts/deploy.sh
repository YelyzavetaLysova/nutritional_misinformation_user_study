#!/bin/zsh
# Deployment script for nutritional_misinformation_user_study

echo "Starting deployment to server at 158.39.74.209..."

# Ensure we're in the right directory
cd "$(dirname "$0")" || exit
cd ..

# Set the SSH key file to use NREC key
SSH_KEY_FILE="$HOME/.ssh/nrec_key"
echo "Using SSH key file at $SSH_KEY_FILE"

# Add the server to known_hosts if it's not already there
if ! ssh-keygen -F 158.39.74.209 > /dev/null; then
  echo "Adding server to known_hosts..."
  ssh-keyscan -H 158.39.74.209 >> ~/.ssh/known_hosts
fi

# Test SSH connection
echo "Testing SSH connection..."
# Try to connect with the most common cloud instance username
SSH_USER="ubuntu"
echo "Trying to connect as $SSH_USER..."
if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o IdentitiesOnly=yes -i "$SSH_KEY_FILE" $SSH_USER@158.39.74.209 "echo 'SSH connection successful as $SSH_USER'"; then
  echo "Connection successful as $SSH_USER!"
else
  echo "Failed to connect as $SSH_USER, trying alternative usernames..."
  for user in azureuser admin root liza yelyzavetalysova lizal ubuntu-server; do
    echo "Trying to connect as $user..."
    if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o IdentitiesOnly=yes -i "$SSH_KEY_FILE" $user@158.39.74.209 "echo 'SSH connection successful as $user'"; then
      echo "Connection successful as $user!"
      SSH_USER=$user
      break
    fi
  done
fi

if [ -z "$SSH_USER" ]; then
  echo "SSH connection failed with all attempted usernames. Please check your SSH key and server configuration."
  exit 1
fi

# Deploy using rsync
echo "Deploying application files..."
rsync -avz --exclude 'venv' --exclude '.git' --exclude '__pycache__' --exclude 'logs/*.log' \
  --exclude 'data/responses/*.json' --exclude 'data/responses/*.csv' \
  -e "ssh -i $SSH_KEY_FILE" \
  ./ ${SSH_USER}@158.39.74.209:~/nutritional_misinformation_user_study/

# Run the remote setup script
echo "Setting up application on the server..."
ssh -i "$SSH_KEY_FILE" ${SSH_USER}@158.39.74.209 'bash -s' << 'EOF'
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
    server_name 158.39.74.209;

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
