#!/bin/zsh
# Script to update the application on the server

echo "Updating nutritional_misinformation_user_study on the server..."

SSH_KEY_FILE="$HOME/.ssh/nrec_key"

# Check if the SSH key file exists
if [[ ! -f "$SSH_KEY_FILE" ]]; then
  echo "SSH key not found at $SSH_KEY_FILE. Please run the deploy script first."
  exit 1
fi

# Run the update commands on the server
ssh -i "$SSH_KEY_FILE" ubuntu@10.1.1.140 'bash -s' << 'EOF'
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
