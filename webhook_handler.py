from flask import Flask, request, jsonify
from twilio.twiml import VoiceResponse
import logging
import os
from datetime import datetime
from dotenv import load_dotenv
import requests

load_dotenv()
logger = logging.getLogger("webhook-handler")

app = Flask(__name__)

# Configuration
LIVEKIT_URL = os.getenv('LIVEKIT_URL')
LIVEKIT_API_KEY = os.getenv('LIVEKIT_API_KEY')
LIVEKIT_API_SECRET = os.getenv('LIVEKIT_API_SECRET')


@app.route('/twiml/outbound', methods=['POST'])
def outbound_call_handler():
    """
    Handle outbound calls by connecting them to LiveKit.
    This endpoint generates TwiML to connect the call to your LiveKit room.
    """
    logger.info("Received outbound call webhook")
    
    # Get call information from Twilio
    call_sid = request.values.get('CallSid')
    from_number = request.values.get('From')
    to_number = request.values.get('To')
    call_status = request.values.get('CallStatus')
    
    logger.info(f"Call {call_sid}: {call_status} from {from_number} to {to_number}")
    
    # Create TwiML response
    response = VoiceResponse()
    
    # Check if this is an answering machine
    answered_by = request.values.get('AnsweredBy')
    if answered_by == 'machine_start':
        # Handle answering machine - you can leave a voicemail or hang up
        logger.info(f"Call {call_sid}: Answering machine detected")
        response.say("Hello! This is an automated message from AI Entity. We'll try calling back later.")
        response.hangup()
        return str(response)
    
    if call_status == 'in-progress':
        # Generate a unique room name for this call
        room_name = f"outbound-{call_sid}"
        
        # Connect to LiveKit room via SIP
        # You'll need to configure LiveKit SIP ingress for this to work
        sip_uri = f"sip:{room_name}@{LIVEKIT_URL.replace('wss://', '').replace('ws://', '')}"
        
        # Alternative: Use Twilio's <Connect> verb to bridge to LiveKit
        # This requires setting up LiveKit's SIP bridge
        connect = response.connect()
        connect.stream(url=f"wss://{LIVEKIT_URL}/sip/{room_name}")
        
        # Or use a simpler approach with <Dial>
        # response.dial(sip_uri)
        
        logger.info(f"Connected call {call_sid} to LiveKit room: {room_name}")
    else:
        # Call not answered or other status
        response.say("We're unable to connect your call at this time. Please try again later.")
        response.hangup()
    
    return str(response)


@app.route('/twiml/inbound', methods=['POST'])
def inbound_call_handler():
    """
    Handle inbound calls (existing functionality).
    """
    logger.info("Received inbound call webhook")
    
    call_sid = request.values.get('CallSid')
    from_number = request.values.get('From')
    to_number = request.values.get('To')
    
    logger.info(f"Inbound call {call_sid}: from {from_number} to {to_number}")
    
    response = VoiceResponse()
    
    # Create room name and connect to LiveKit
    room_name = f"inbound-{call_sid}"
    
    # Connect to LiveKit
    connect = response.connect()
    connect.stream(url=f"wss://{LIVEKIT_URL}/sip/{room_name}")
    
    return str(response)


@app.route('/webhook/call-status', methods=['POST'])
def call_status_webhook():
    """
    Handle call status updates from Twilio.
    This webhook receives updates about call progress.
    """
    call_sid = request.values.get('CallSid')
    call_status = request.values.get('CallStatus')
    call_duration = request.values.get('CallDuration')
    timestamp = request.values.get('Timestamp')
    
    logger.info(f"Call status update - SID: {call_sid}, Status: {call_status}, Duration: {call_duration}")
    
    # Here you can update your database or trigger other actions based on call status
    status_data = {
        'call_sid': call_sid,
        'status': call_status,
        'duration': call_duration,
        'timestamp': timestamp,
        'from': request.values.get('From'),
        'to': request.values.get('To'),
        'direction': request.values.get('Direction')
    }
    
    # Log call completion
    if call_status in ['completed', 'failed', 'busy', 'no-answer']:
        log_call_completion(status_data)
    
    # Update your outbound caller results if needed
    update_outbound_caller_status(call_sid, call_status, call_duration)
    
    return jsonify({'status': 'received'})


@app.route('/webhook/recording-status', methods=['POST'])
def recording_status_webhook():
    """
    Handle recording status updates from Twilio.
    """
    call_sid = request.values.get('CallSid')
    recording_sid = request.values.get('RecordingSid')
    recording_url = request.values.get('RecordingUrl')
    recording_status = request.values.get('RecordingStatus')
    
    logger.info(f"Recording update - Call: {call_sid}, Recording: {recording_sid}, Status: {recording_status}")
    
    if recording_status == 'completed':
        # Download and store the recording if needed
        download_recording(recording_sid, recording_url)
    
    return jsonify({'status': 'received'})


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'livekit-twilio-webhook-handler'
    })


def log_call_completion(status_data):
    """
    Log completed call information.
    You can extend this to write to a database or external service.
    """
    logger.info(f"Call completed: {status_data}")
    
    # Example: Write to database
    # db.call_logs.insert_one({
    #     'call_sid': status_data['call_sid'],
    #     'status': status_data['status'],
    #     'duration': int(status_data['duration']) if status_data['duration'] else 0,
    #     'from_number': status_data['from'],
    #     'to_number': status_data['to'],
    #     'direction': status_data['direction'],
    #     'completed_at': datetime.now()
    # })


def update_outbound_caller_status(call_sid, status, duration):
    """
    Update the outbound caller with call status.
    This would integrate with your OutboundCaller class.
    """
    # In a production setup, you'd have a shared state or database
    # to communicate between the webhook handler and outbound caller
    pass


def download_recording(recording_sid, recording_url):
    """
    Download call recording from Twilio.
    """
    try:
        # Add authentication to the request
        auth = (os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))
        response = requests.get(recording_url, auth=auth)
        
        if response.status_code == 200:
            # Save recording to file or cloud storage
            filename = f"recording_{recording_sid}.mp3"
            with open(f"recordings/{filename}", 'wb') as f:
                f.write(response.content)
            logger.info(f"Downloaded recording: {filename}")
        else:
            logger.error(f"Failed to download recording: {response.status_code}")
            
    except Exception as e:
        logger.error(f"Error downloading recording {recording_sid}: {e}")


if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create recordings directory
    os.makedirs('recordings', exist_ok=True)
    
    # Run the Flask app
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('WEBHOOK_PORT', 5000)),
        debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    )
