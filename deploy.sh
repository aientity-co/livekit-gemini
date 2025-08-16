#!/bin/bash

# Google Cloud VM Deployment Script for LiveKit Voice Agent
# This script sets up a VM instance and deploys the application

set -e

# Configuration variables
PROJECT_ID="${PROJECT_ID:-your-project-id}"
ZONE="${ZONE:-us-central1-a}"
INSTANCE_NAME="${INSTANCE_NAME:-livekit-voice-agent}"
MACHINE_TYPE="${MACHINE_TYPE:-e2-medium}"
DISK_SIZE="${DISK_SIZE:-50GB}"
IMAGE_FAMILY="${IMAGE_FAMILY:-debian-11}"
IMAGE_PROJECT="${IMAGE_PROJECT:-debian-cloud}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting LiveKit Voice Agent deployment on Google Cloud...${NC}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if required environment variables are set
if [ -z "$PROJECT_ID" ] || [ "$PROJECT_ID" = "your-project-id" ]; then
    echo -e "${RED}Error: PROJECT_ID is not set. Please set it to your Google Cloud project ID.${NC}"
    exit 1
fi

# Set the project
echo -e "${YELLOW}Setting project to: $PROJECT_ID${NC}"
gcloud config set project $PROJECT_ID

# Enable required APIs
echo -e "${YELLOW}Enabling required APIs...${NC}"
gcloud services enable compute.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Create firewall rules for the application
echo -e "${YELLOW}Creating firewall rules...${NC}"
gcloud compute firewall-rules create livekit-voice-agent-http \
    --allow tcp:8000 \
    --description "Allow HTTP traffic to LiveKit Voice Agent API" \
    --direction INGRESS \
    --source-ranges 0.0.0.0/0 \
    --target-tags livekit-voice-agent || true

gcloud compute firewall-rules create livekit-voice-agent-livekit \
    --allow tcp:7880,tcp:7881,udp:7882 \
    --description "Allow LiveKit server traffic" \
    --direction INGRESS \
    --source-ranges 0.0.0.0/0 \
    --target-tags livekit-voice-agent || true

# Create startup script
cat > startup-script.sh << 'EOF'
#!/bin/bash

# Update system
apt-get update
apt-get install -y curl wget git

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
usermod -aG docker $USER

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create application directory
mkdir -p /opt/livekit-voice-agent
cd /opt/livekit-voice-agent

# Clone the repository (you'll need to set up a git repository)
# git clone https://github.com/your-username/livekit-gemini.git .

# Create keys directory
mkdir -p keys

# Create environment file template
cat > .env << 'ENVEOF'
# LiveKit server
LIVEKIT_URL=http://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret

# Google credentials (you'll need to upload your service account key)
GOOGLE_APPLICATION_CREDENTIALS=/opt/livekit-voice-agent/keys/service-account.json
GOOGLE_API_KEY=your-gemini-api-key

# SIP configuration
SIP_OUTBOUND_TRUNK_ID=your-sip-trunk-id

# Optional: Deepgram/Cartesia keys
DEEPGRAM_API_KEY=your-deepgram-key
CARTESIA_API_KEY=your-cartesia-key
CARTESIA_VOICE_ID=your-cartesia-voice-id
ENVEOF

# Start the application
docker-compose up -d

# Create systemd service for auto-restart
cat > /etc/systemd/system/livekit-voice-agent.service << 'SERVICEEOF'
[Unit]
Description=LiveKit Voice Agent
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/livekit-voice-agent
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
SERVICEEOF

systemctl enable livekit-voice-agent.service
systemctl start livekit-voice-agent.service
EOF

# Create the VM instance
echo -e "${YELLOW}Creating VM instance: $INSTANCE_NAME${NC}"
gcloud compute instances create $INSTANCE_NAME \
    --zone=$ZONE \
    --machine-type=$MACHINE_TYPE \
    --boot-disk-size=$DISK_SIZE \
    --image-family=$IMAGE_FAMILY \
    --image-project=$IMAGE_PROJECT \
    --tags=livekit-voice-agent \
    --metadata-from-file startup-script=startup-script.sh \
    --scopes=cloud-platform

# Wait for the instance to be ready
echo -e "${YELLOW}Waiting for instance to be ready...${NC}"
sleep 60

# Get the external IP
EXTERNAL_IP=$(gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --format="value(networkInterfaces[0].accessConfigs[0].natIP)")

echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${GREEN}Instance IP: $EXTERNAL_IP${NC}"
echo -e "${GREEN}API endpoint: http://$EXTERNAL_IP:8000${NC}"
echo -e "${GREEN}Health check: http://$EXTERNAL_IP:8000/health${NC}"
echo -e "${GREEN}API documentation: http://$EXTERNAL_IP:8000/docs${NC}"

echo -e "${YELLOW}Next steps:${NC}"
echo -e "1. Upload your service account key to: /opt/livekit-voice-agent/keys/service-account.json"
echo -e "2. Update the .env file with your API keys"
echo -e "3. Restart the application: sudo systemctl restart livekit-voice-agent"

# Clean up startup script
rm startup-script.sh
