## LiveKit + Gemini Voice Agent with Twilio Outbound Calling

AI-powered voice agent that handles both inbound and outbound calls using LiveKit Agents with Google Gemini, Deepgram STT, Cartesia TTS, and Twilio telephony integration.

### Features

- **Inbound Calling**: Handle incoming calls through Twilio webhooks
- **Outbound Calling**: Initiate calls programmatically with contact management
- **AI Voice Agent**: Powered by Google Gemini 2.5 Flash for intelligent conversations
- **High-Quality Audio**: Deepgram Nova-3 STT and Cartesia Sonic-2 TTS
- **Call Management**: Track call results, recordings, and campaign analytics
- **Webhook Integration**: Real-time call status updates and event handling

### Prerequisites
- Python 3.10–3.12
- LiveKit Cloud account or self-hosted LiveKit server
- Twilio account with phone number
- Google Cloud account (for Gemini API)
- Deepgram account (for STT)
- Cartesia account (for TTS)
- HTTPS endpoint for webhooks (use ngrok for development)

### 1) Create and activate a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt
```

### 2) Configure environment
This project loads environment variables from a `.env` file.

Copy `.env.example` to `.env` and configure the following keys:
```bash
# LiveKit Configuration
LIVEKIT_URL=wss://your-livekit-instance.livekit.cloud
LIVEKIT_API_KEY=your-livekit-api-key
LIVEKIT_API_SECRET=your-livekit-api-secret

# Twilio Configuration
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_PHONE_NUMBER=+1234567890

# Webhook Configuration
WEBHOOK_BASE_URL=https://your-server.com

# AI Service API Keys
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account.json
DEEPGRAM_API_KEY=your-deepgram-api-key
CARTESIA_API_KEY=your-cartesia-api-key

# Optional: Database and Redis
DATABASE_URL=postgresql://user:password@localhost:5432/livekit_calls
REDIS_URL=redis://localhost:6379
```

You can generate the Google service account and enable required APIs using the helper script:
```bash
# Required: set your GCP project id
PROJECT_ID="your-gcp-project" \
SA_NAME="livekit-voice-agent" \
KEY_PATH="$HOME/keys/livekit-voice-agent.json" \
GOOGLE_API_KEY="your-gemini-api-key" \
bash glcoud.sh
```
The script enables Speech-to-Text and Text-to-Speech APIs, creates a service account, binds minimal roles, and writes a JSON key to `KEY_PATH`.

### 3) Run a LiveKit server (not required for local)
Pick one of the following.

- Dev (local, quick start):
```bash
livekit-server --dev --bind 0.0.0.0
```

- Docker (dev):
```bash
docker run --rm -it \
  -p 7880:7880 -p 7881:7881 -p 7882:7882/udp \
  livekit/livekit-server --dev
```

- Prod with config file (Docker):
```bash
docker run -d --name livekit \
  -p 7880:7880 -p 7881:7881 -p 7882:7882/udp \
  -v /absolute/path/to/livekit.yaml:/config/livekit.yaml:ro \
  livekit/livekit-server --config /config/livekit.yaml
```

Default ports to open: 7880 (HTTP API), 7881/TCP (ICE/TURN), 7882/UDP (RTP).

### 4) Set up Twilio Webhooks

Configure your Twilio phone number with the following webhook URLs:

**Voice Configuration:**
- Voice URL: `https://your-server.com/twiml/inbound`
- HTTP Method: POST
- Fallback URL: `https://your-server.com/twiml/fallback`

**Status Callbacks:**
- Status Callback URL: `https://your-server.com/webhook/call-status`
- Status Callback Events: `initiated`, `ringing`, `answered`, `completed`

### 5) Deploy the Webhook Handler

Start the webhook server to handle Twilio events:
```bash
# Development (with ngrok)
python webhook_handler.py

# Production (with proper HTTPS)
gunicorn -w 4 -b 0.0.0.0:5000 webhook_handler:app
```

For development, use ngrok to expose your local server:
```bash
ngrok http 5000
# Use the https URL as your WEBHOOK_BASE_URL
```

### 6) Run the Voice Agent

Start the LiveKit voice agent:
```bash
# For inbound calls
python telephony_agent.py

# Alternative agent (older version)
python livekit_gemini.py
```

### 7) Make Outbound Calls

Use the provided scripts to initiate outbound calls:

**Single Call:**
```bash
python make_calls.py single --name "John Doe" --phone "+1234567890" --company "Test Corp"
```

**Bulk Calls from CSV:**
```bash
# Create sample CSV file
python make_calls.py sample-csv

# Make bulk calls
python make_calls.py bulk --file sample_contacts.csv --delay 30
```

**Bulk Calls from JSON:**
```bash
# Create sample JSON file
python make_calls.py sample-json

# Make bulk calls
python make_calls.py bulk --file sample_contacts.json --delay 45
```

### 5) Optional: Console operations with livekit-cli
Set these env vars once to avoid repeating flags:
```bash
export LIVEKIT_URL=http://localhost:7880
export LIVEKIT_API_KEY=<API_KEY>
export LIVEKIT_API_SECRET=<API_SECRET>
```

Examples:
```bash
# Create a join token
livekit-cli create-token --join --room <ROOM_NAME> --identity <USER_IDENTITY> --valid-for 24h

# Rooms and participants
livekit-cli list-rooms
livekit-cli list-participants --room <ROOM_NAME>
livekit-cli remove-participant --room <ROOM_NAME> --identity <USER_IDENTITY>

# Room management
livekit-cli create-room --name <ROOM_NAME>
livekit-cli delete-room --room <ROOM_NAME>

# Ingress / Egress (optional)
livekit-cli create-ingress --input-type RTMP --name <STREAM> --room <ROOM> --identity <USER>
livekit-cli list-ingress
livekit-cli delete-ingress --ingress-id <INGRESS_ID>
livekit-cli list-egress
livekit-cli stop-egress --egress-id <EGRESS_ID>
```

### File Structure

```
livekit-gemini/
├── telephony_agent.py       # Main voice agent for handling calls
├── outbound_caller.py        # Outbound calling functionality
├── webhook_handler.py        # Twilio webhook handler (Flask app)
├── make_calls.py            # CLI tool for initiating calls
├── sip_config.py            # SIP configuration utilities
├── system_prompt.py         # AI agent system prompt
├── requirements.txt         # Python dependencies
├── .env.example            # Environment variables template
└── README.md              # This file
```

### API Usage Examples

**Making Calls Programmatically:**
```python
from outbound_caller import OutboundCaller, CallRecipient
import asyncio

async def make_call_example():
    caller = OutboundCaller()
    
    recipient = CallRecipient(
        name="Jane Smith",
        phone_number="+1234567890",
        company="Example Corp",
        notes="Follow up on demo request"
    )
    
    result = await caller.make_outbound_call(recipient)
    print(f"Call result: {result.status}")

asyncio.run(make_call_example())
```

**Bulk Calling:**
```python
recipients = [
    CallRecipient("Alice Johnson", "+1234567891", "Tech Corp"),
    CallRecipient("Bob Wilson", "+1234567892", "Sales Inc"),
]

results = await caller.make_bulk_calls(recipients, delay_between_calls=30)
summary = caller.get_campaign_summary()
```

### Contact File Formats

**CSV Format (sample_contacts.csv):**
```csv
name,phone,company,notes
John Smith,+1234567890,Tech Corp,Potential lead from website
Jane Doe,+1234567891,Marketing Inc,Interested in AI solutions
```

**JSON Format (sample_contacts.json):**
```json
[
  {
    "name": "John Smith",
    "phone": "+1234567890",
    "company": "Tech Corp",
    "notes": "Potential lead from website"
  }
]
```

### Webhook Events

The webhook handler processes the following Twilio events:

- **Call Status Updates**: `initiated`, `ringing`, `answered`, `completed`, `failed`
- **Recording Status**: `completed` recordings are automatically downloaded
- **Machine Detection**: Handles answering machines appropriately

### Monitoring and Analytics

**Call Results Tracking:**
- Automatic call status updates via webhooks
- Campaign summary with success rates
- Individual call duration and outcome tracking
- Error handling and retry logic

**Logging:**
All components include comprehensive logging for debugging and monitoring:
```bash
# View logs
tail -f agent.log

# Set log level
export LOG_LEVEL=DEBUG
```

### Customization

**System Prompt:**
Edit `system_prompt.py` to customize your AI agent's personality and responses.

**Voice Settings:**
Modify voice parameters in `telephony_agent.py`:
- TTS voice ID (Cartesia)
- STT model (Deepgram) 
- VAD sensitivity (Silero)

**Call Flow:**
Customize call handling in `webhook_handler.py`:
- Answering machine detection
- Call routing logic  
- Recording preferences

### Troubleshooting

**Common Issues:**

1. **Webhook Not Receiving Events:**
   - Verify HTTPS is working (use ngrok for development)
   - Check Twilio webhook configuration
   - Ensure webhook URL is publicly accessible

2. **Calls Not Connecting:**
   - Verify Twilio credentials and phone number
   - Check LiveKit SIP configuration
   - Ensure agent is running and accessible

3. **Audio Quality Issues:**
   - Check network connectivity
   - Verify API keys for STT/TTS services
   - Monitor Deepgram and Cartesia usage limits

4. **Environment Issues:**
   - Validate all environment variables are set
   - Check file paths for service account credentials
   - Verify API permissions and quotas

**Debug Commands:**
```bash
# Test outbound calling configuration
python -c "from outbound_caller import OutboundCaller; OutboundCaller()"

# Test SIP configuration
python sip_config.py

# Validate environment
python -c "import os; print([k for k in os.environ if 'TWILIO' in k or 'LIVEKIT' in k])"
```

### Support

For issues and questions:
- LiveKit Docs: https://docs.livekit.io/
- Twilio Voice API: https://www.twilio.com/docs/voice
- GitHub Issues: Create an issue with logs and configuration details


