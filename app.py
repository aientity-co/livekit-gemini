from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import asyncio
import logging
from typing import Optional
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="LiveKit Voice Agent API",
    description="API for making outbound voice calls using LiveKit and Gemini",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response
class CallRequest(BaseModel):
    phone_number: str
    customer_name: Optional[str] = None
    appointment_date: Optional[str] = None
    appointment_time: Optional[str] = None
    custom_instructions: Optional[str] = None

class CallResponse(BaseModel):
    call_id: str
    status: str
    message: str

class HealthResponse(BaseModel):
    status: str
    message: str

# In-memory storage for call status (use a proper database in production)
call_status = {}

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        message="LiveKit Voice Agent API is running"
    )

@app.post("/call", response_model=CallResponse)
async def make_call(request: CallRequest, background_tasks: BackgroundTasks):
    """Make an outbound call to the specified phone number"""
    try:
        # Validate phone number format (basic validation)
        if not request.phone_number or len(request.phone_number) < 10:
            raise HTTPException(status_code=400, detail="Invalid phone number")
        
        # Generate a unique call ID
        import uuid
        call_id = str(uuid.uuid4())
        
        # Store initial call status
        call_status[call_id] = {
            "status": "initiated",
            "phone_number": request.phone_number,
            "customer_name": request.customer_name,
            "appointment_date": request.appointment_date,
            "appointment_time": request.appointment_time,
            "custom_instructions": request.custom_instructions
        }
        
        # Start the call in the background
        background_tasks.add_task(
            initiate_call,
            call_id,
            request.phone_number,
            request.customer_name,
            request.appointment_date,
            request.appointment_time,
            request.custom_instructions
        )
        
        logger.info(f"Call initiated for {request.phone_number} with ID: {call_id}")
        
        return CallResponse(
            call_id=call_id,
            status="initiated",
            message=f"Call to {request.phone_number} has been initiated"
        )
        
    except Exception as e:
        logger.error(f"Error initiating call: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to initiate call: {str(e)}")

@app.get("/call/{call_id}")
async def get_call_status(call_id: str):
    """Get the status of a specific call"""
    if call_id not in call_status:
        raise HTTPException(status_code=404, detail="Call not found")
    
    return call_status[call_id]

@app.get("/calls")
async def list_calls():
    """List all calls"""
    return {"calls": call_status}

async def initiate_call(call_id: str, phone_number: str, customer_name: str = None, 
                       appointment_date: str = None, appointment_time: str = None, 
                       custom_instructions: str = None):
    """Background task to initiate the actual call using LiveKit"""
    try:
        # Update call status
        call_status[call_id]["status"] = "connecting"
        
        # Import LiveKit API
        from livekit import api
        
        # Get LiveKit configuration from environment
        livekit_url = os.getenv("LIVEKIT_URL")
        api_key = os.getenv("LIVEKIT_API_KEY")
        api_secret = os.getenv("LIVEKIT_API_SECRET")
        sip_trunk_id = os.getenv("SIP_OUTBOUND_TRUNK_ID")
        
        if not all([livekit_url, api_key, api_secret, sip_trunk_id]):
            raise Exception("Missing LiveKit configuration")
        
        # Create LiveKit API client
        livekit_api = api.LiveKitAPI(
            url=livekit_url,
            api_key=api_key,
            api_secret=api_secret
        )
        
        # Create a unique room name for this call
        room_name = f"call-{call_id}"
        
        # Create the room
        await livekit_api.room.create_room(
            api.CreateRoomRequest(
                name=room_name,
                empty_timeout=300,  # 5 minutes
                max_participants=2
            )
        )
        
        # Update call status
        call_status[call_id]["status"] = "dialing"
        call_status[call_id]["room_name"] = room_name
        
        # Create SIP participant to dial the phone number
        await livekit_api.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                room_name=room_name,
                sip_trunk_id=sip_trunk_id,
                sip_call_to=phone_number,
                participant_identity="phone_user"
            )
        )
        
        # Update call status
        call_status[call_id]["status"] = "connected"
        call_status[call_id]["message"] = "Call connected successfully"
        
        logger.info(f"Call {call_id} connected to {phone_number}")
        
    except Exception as e:
        logger.error(f"Error in call {call_id}: {str(e)}")
        call_status[call_id]["status"] = "failed"
        call_status[call_id]["error"] = str(e)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
