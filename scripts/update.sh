#!/bin/zsh
# Script to update the application on the server

echo "Updating nutritional_misinformation_user_study on the server..."

SSH_KEY_FILE="$HOME/.ssh/nrec_key"

# Check if the SSH key file exists
if [[ ! -f "$SSH_KEY_FILE" ]]; then
  echo "SSH key not found at $SSH_KEY_FILE. Please run the deploy script first."
  exit 1
fi

# Check which username works
echo "Testing SSH connection..."
for user in ubuntu ubuntu-server admin administrator root liza yelyzavetalysova lizal; do
  if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -i "$SSH_KEY_FILE" $user@158.39.74.209 "echo 'SSH connection successful'" &>/dev/null; then
    SSH_USER=$user
    break
  fi
done

if [ -z "$SSH_USER" ]; then
  echo "SSH connection failed with all attempted usernames. Please check your SSH key and server configuration."
  exit 1
fi

# Run the update commands on the server
ssh -i "$SSH_KEY_FILE" ${SSH_USER}@158.39.74.209 'bash -s' << 'EOF'
  cd ~/nutritional_misinformation_user_study
  
  # Pull the latest changes from GitHub
  echo "Pulling latest changes..."
  git pull
  
  # Update dependencies
  echo "Updating dependencies..."
  source venv/bin/activate
  pip install -r requirements.txt
  
  # Restart the application
  echo "Restarting the application..."
  sudo systemctl restart nutritional-survey
  
  # Show service status
  echo "Service status:"
  sudo systemctl status nutritional-survey --no-pager
EOF

echo "Update completed."
