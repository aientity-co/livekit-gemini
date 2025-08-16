## LiveKit + Gemini Voice Agent

Minimal agent that uses LiveKit Agents with Google Gemini 1.5, Google STT/TTS, and Silero VAD.

## Prerequisites
- Python 3.10–3.12
- Docker (optional, for running LiveKit server)
- livekit-cli (optional, for console operations)

## Setup

### 1) Create and activate a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt
```

### 2) Configure environment
This project loads environment variables from a `.env` file (or `.env.local` for development).

Create `.env` in the project root with the following keys:
```bash
# LiveKit server
LIVEKIT_URL=http://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret

# Google (choose either service account or API key as needed)
# Path to a Google service account JSON key file
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/your-service-account.json

# Optional: API key for Gemini
GOOGLE_API_KEY=your-gemini-api-key

# Optional: For outbound calling (SIP trunk ID from LiveKit dashboard)
SIP_OUTBOUND_TRUNK_ID=your-sip-trunk-id

# Optional: Deepgram/Cartesia keys for alternative STT/TTS
DEEPGRAM_API_KEY=your-deepgram-key
CARTESIA_API_KEY=your-cartesia-key
CARTESIA_VOICE_ID=your-cartesia-voice-id
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

## Running the Agent

### Basic Voice Agent (livekit_gemini.py)
The entrypoint is in `livekit_gemini.py` and relies on the environment variables above.

Common commands:
```bash
# Start in dev mode
python3 livekit_gemini.py dev

# Connect the agent to a specific room
python3 livekit_gemini.py connect --room test-voice
```

### Outbound Caller Agent (agent.py)
This script implements an outbound calling agent using SIP for scheduling confirmations.

```bash
python3 agent.py
```

- Ensure `SIP_OUTBOUND_TRUNK_ID` is set in `.env`.
- The agent dials a phone number provided via job metadata and confirms appointments.

## Optional: Console operations with livekit-cli
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

## Troubleshooting
- If audio fails to connect from remote clients, ensure ports 7881/TCP and 7882/UDP are reachable and NAT/ICE is configured in `livekit.yaml` for public deployments.
- Verify `GOOGLE_APPLICATION_CREDENTIALS` points to a valid service account JSON and that Speech-to-Text/Text-to-Speech APIs are enabled.
- Check `.env` is being loaded (the script calls `dotenv.load_dotenv(override=True)`).
- **User inputs skipped**: If logs show "skipping user input, speech scheduling is paused", ensure no unnecessary `session.drain()` calls are present after greetings—the agent session should remain active to process inputs.


