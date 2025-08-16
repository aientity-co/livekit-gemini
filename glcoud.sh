#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   PROJECT_ID="your-project" \
#   SA_NAME="livekit-voice-agent" \
#   KEY_PATH="$HOME/keys/livekit-voice-agent.json" \
#   GOOGLE_API_KEY="your-gemini-api-key" \
#   bash glcoud.sh
#
# Optional: ALLOW_EDITOR_FALLBACK=true to allow roles/editor if Text-to-Speech roles fail.

log() { echo "[$(date +%H:%M:%S)] $*"; }

PROJECT_ID=${PROJECT_ID:-}
SA_NAME=${SA_NAME:-livekit-voice-agent}
KEY_PATH=${KEY_PATH:-"$HOME/keys/${SA_NAME}.json"}
GOOGLE_API_KEY=${GOOGLE_API_KEY:-}
ALLOW_EDITOR_FALLBACK=${ALLOW_EDITOR_FALLBACK:-false}

if [[ -z "$PROJECT_ID" ]]; then
  echo "ERROR: Set PROJECT_ID environment variable." >&2
  exit 1
fi

SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

log "Authenticating and selecting project..."
# Best effort auth; skip if already authenticated
if ! gcloud config get-value account >/dev/null 2>&1; then
  gcloud auth login --brief || true
fi
gcloud config set project "$PROJECT_ID" | cat

log "Enabling required APIs (Speech-to-Text, Text-to-Speech)..."
gcloud services enable speech.googleapis.com texttospeech.googleapis.com | cat

log "Creating service account if missing: $SA_EMAIL"
if ! gcloud iam service-accounts describe "$SA_EMAIL" >/dev/null 2>&1; then
  gcloud iam service-accounts create "$SA_NAME" \
    --display-name "LiveKit Voice Agent" | cat
else
  log "Service account already exists."
fi

bind_role() {
  local role="$1"
  if gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="$role" >/dev/null 2>&1; then
    echo "$role"; return 0
  else
    return 1
  fi
}

log "Granting minimal roles..."
# Always Speech Client
if bind_role "roles/speech.client"; then
  log "Granted roles/speech.client"
else
  log "WARN: Could not grant roles/speech.client (might already be bound)"
fi

# Try TTS roles in order of least to most privileged
TTS_ROLE=""
if bind_role "roles/texttospeech.user"; then
  TTS_ROLE="roles/texttospeech.user"
  log "Granted roles/texttospeech.user"
elif bind_role "roles/texttospeech.editor"; then
  TTS_ROLE="roles/texttospeech.editor"
  log "Granted roles/texttospeech.editor"
elif bind_role "roles/texttospeech.admin"; then
  TTS_ROLE="roles/texttospeech.admin"
  log "Granted roles/texttospeech.admin"
else
  if [[ "$ALLOW_EDITOR_FALLBACK" == "true" ]]; then
    if bind_role "roles/editor"; then
      TTS_ROLE="roles/editor"
      log "Granted roles/editor as a temporary fallback (tighten later)"
    else
      log "ERROR: Failed to grant any Text-to-Speech role (user/editor/admin) and editor fallback is not available."
    fi
  else
    log "WARN: Failed to grant any Text-to-Speech role (user/editor/admin). Set ALLOW_EDITOR_FALLBACK=true to try roles/editor."
  fi
fi

log "Creating service account key at: $KEY_PATH"
mkdir -p "$(dirname "$KEY_PATH")"
if [[ -f "$KEY_PATH" ]]; then
  log "Key already exists at $KEY_PATH (skipping creation)"
else
  gcloud iam service-accounts keys create "$KEY_PATH" \
    --iam-account "$SA_EMAIL" | cat
fi

cat <<EOF

Done. Export these before running the agent:

export GOOGLE_APPLICATION_CREDENTIALS="$KEY_PATH"
export GOOGLE_API_KEY="${GOOGLE_API_KEY}"

# Then run:
# cd /Users/gautam/Desktop/livekit-gemini
# python3 lesson4_gemini.py dev
# python3 lesson4_gemini.py connect --room test-voice

EOF
