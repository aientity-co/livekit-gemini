# LiveKit Voice Agent - Google Cloud VM Deployment Guide

This guide will walk you through deploying your LiveKit Voice Agent on Google Cloud VM with an API for making outbound calls.

## Prerequisites

1. **Google Cloud Account**: You need a Google Cloud account with billing enabled
2. **Google Cloud CLI**: Install and configure the `gcloud` CLI tool
3. **Terraform** (optional): For infrastructure as code deployment
4. **Docker**: For local testing
5. **API Keys**: You'll need the following API keys:
   - Google Cloud service account key
   - Google Gemini API key
   - LiveKit SIP trunk ID
   - Deepgram API key (optional)
   - Cartesia API key (optional)

## Method 1: Quick Deployment with Script

### Step 1: Set Environment Variables

```bash
export PROJECT_ID="your-google-cloud-project-id"
export ZONE="us-central1-a"
export INSTANCE_NAME="livekit-voice-agent"
export MACHINE_TYPE="e2-medium"
```

### Step 2: Run the Deployment Script

```bash
./deploy.sh
```

This script will:
- Enable required Google Cloud APIs
- Create firewall rules
- Create a VM instance with the necessary configuration
- Set up Docker and Docker Compose
- Create the application directory structure

### Step 3: Upload Your Application Files

After the VM is created, you need to upload your application files:

```bash
# Get the VM's external IP
EXTERNAL_IP=$(gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --format="value(networkInterfaces[0].accessConfigs[0].natIP)")

# Upload your application files
gcloud compute scp --zone=$ZONE --recurse . $INSTANCE_NAME:/opt/livekit-voice-agent/

# Upload your service account key
gcloud compute scp --zone=$ZONE /path/to/your/service-account.json $INSTANCE_NAME:/opt/livekit-voice-agent/keys/
```

### Step 4: Configure Environment Variables

SSH into the VM and update the environment file:

```bash
gcloud compute ssh --zone=$ZONE $INSTANCE_NAME

# Edit the environment file
sudo nano /opt/livekit-voice-agent/.env
```

Update the following variables:
```bash
GOOGLE_API_KEY=your-actual-gemini-api-key
SIP_OUTBOUND_TRUNK_ID=your-actual-sip-trunk-id
DEEPGRAM_API_KEY=your-actual-deepgram-key
CARTESIA_API_KEY=your-actual-cartesia-key
CARTESIA_VOICE_ID=your-actual-cartesia-voice-id
```

### Step 5: Start the Application

```bash
# Start the application
sudo systemctl start livekit-voice-agent

# Check the status
sudo systemctl status livekit-voice-agent

# View logs
sudo journalctl -u livekit-voice-agent -f
```

## Method 2: Terraform Deployment

### Step 1: Configure Terraform

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:
```hcl
project_id = "your-google-cloud-project-id"
region     = "us-central1"
zone       = "us-central1-a"
```

### Step 2: Deploy Infrastructure

```bash
terraform init
terraform plan
terraform apply
```

### Step 3: Upload Application Files

After Terraform creates the VM, upload your files:

```bash
# Get the external IP from Terraform output
EXTERNAL_IP=$(terraform output -raw external_ip)

# Upload files (you'll need to set up SSH keys first)
scp -r . livekit@$EXTERNAL_IP:/opt/livekit-voice-agent/
scp /path/to/your/service-account.json livekit@$EXTERNAL_IP:/opt/livekit-voice-agent/keys/
```

### Step 4: Configure and Start

SSH into the VM and configure the environment:

```bash
ssh livekit@$EXTERNAL_IP

# Edit environment file
nano /opt/livekit-voice-agent/.env

# Start the application
sudo systemctl start livekit-voice-agent
```

## Method 3: Manual VM Setup

### Step 1: Create VM Instance

```bash
gcloud compute instances create livekit-voice-agent \
  --zone=us-central1-a \
  --machine-type=e2-medium \
  --boot-disk-size=50GB \
  --image-family=debian-11 \
  --image-project=debian-cloud \
  --tags=livekit-voice-agent \
  --metadata-from-file startup-script=startup-script.sh \
  --scopes=cloud-platform
```

### Step 2: Create Firewall Rules

```bash
gcloud compute firewall-rules create livekit-voice-agent-http \
  --allow tcp:8000 \
  --description "Allow HTTP traffic to LiveKit Voice Agent API" \
  --direction INGRESS \
  --source-ranges 0.0.0.0/0 \
  --target-tags livekit-voice-agent

gcloud compute firewall-rules create livekit-voice-agent-livekit \
  --allow tcp:7880,tcp:7881,udp:7882 \
  --description "Allow LiveKit server traffic" \
  --direction INGRESS \
  --source-ranges 0.0.0.0/0 \
  --target-tags livekit-voice-agent
```

### Step 3: Follow Steps 3-5 from Method 1

## Testing the Deployment

### 1. Check Health Endpoint

```bash
curl http://$EXTERNAL_IP:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "message": "LiveKit Voice Agent API is running"
}
```

### 2. Make a Test Call

```bash
curl -X POST "http://$EXTERNAL_IP:8000/call" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+1234567890",
    "customer_name": "Test User",
    "appointment_date": "2024-01-15",
    "appointment_time": "2:00 PM"
  }'
```

### 3. Check API Documentation

Open your browser and go to:
```
http://$EXTERNAL_IP:8000/docs
```

## Monitoring and Logs

### View Application Logs

```bash
# SSH into the VM
gcloud compute ssh --zone=$ZONE $INSTANCE_NAME

# View Docker logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f voice-agent-api
docker-compose logs -f voice-agent-worker
docker-compose logs -f livekit-server
```

### Check Service Status

```bash
# Check systemd service status
sudo systemctl status livekit-voice-agent

# Check Docker containers
docker ps
docker-compose ps
```

## Troubleshooting

### Common Issues

1. **Service won't start**
   ```bash
   # Check logs
   sudo journalctl -u livekit-voice-agent -f
   
   # Check Docker status
   sudo systemctl status docker
   ```

2. **API not accessible**
   ```bash
   # Check firewall rules
   gcloud compute firewall-rules list
   
   # Check if port is open
   netstat -tlnp | grep 8000
   ```

3. **LiveKit connection issues**
   ```bash
   # Check LiveKit server logs
   docker-compose logs livekit-server
   
   # Verify environment variables
   cat /opt/livekit-voice-agent/.env
   ```

4. **Missing API keys**
   ```bash
   # Verify service account key exists
   ls -la /opt/livekit-voice-agent/keys/
   
   # Check file permissions
   chmod 600 /opt/livekit-voice-agent/keys/service-account.json
   ```

### Performance Optimization

1. **Increase VM resources** if needed:
   ```bash
   gcloud compute instances set-machine-type $INSTANCE_NAME \
     --machine-type e2-standard-4 \
     --zone=$ZONE
   ```

2. **Add monitoring**:
   ```bash
   # Install monitoring tools
   sudo apt-get install -y htop iotop
   ```

## Security Considerations

1. **Update firewall rules** to restrict access:
   ```bash
   # Only allow specific IP ranges
   gcloud compute firewall-rules update livekit-voice-agent-http \
     --source-ranges YOUR_IP_RANGE
   ```

2. **Add authentication** to the API (implement API keys or JWT)

3. **Use HTTPS** in production (set up SSL certificates)

4. **Regular security updates**:
   ```bash
   sudo apt-get update && sudo apt-get upgrade -y
   ```

## Cost Optimization

1. **Use preemptible instances** for development/testing
2. **Set up auto-shutdown** for non-production environments
3. **Monitor usage** with Google Cloud Console
4. **Use committed use discounts** for production workloads

## Backup and Recovery

1. **Backup configuration**:
   ```bash
   # Create backup of configuration
   tar -czf backup-$(date +%Y%m%d).tar.gz /opt/livekit-voice-agent/
   ```

2. **Create disk snapshots**:
   ```bash
   gcloud compute disks snapshot $INSTANCE_NAME \
     --snapshot-names livekit-voice-agent-backup-$(date +%Y%m%d) \
     --zone=$ZONE
   ```

## Next Steps

1. Set up monitoring and alerting
2. Implement proper authentication
3. Add HTTPS/SSL certificates
4. Set up automated backups
5. Configure log aggregation
6. Implement rate limiting
7. Add API versioning
