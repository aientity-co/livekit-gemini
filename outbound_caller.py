import asyncio
import logging
import os
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
from twilio.rest import Client
from twilio.base.exceptions import TwilioException
import phonenumbers
from phonenumbers import NumberParseException
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("outbound-caller")

@dataclass
class CallRecipient:
    """Data class for call recipient information."""
    name: str
    phone_number: str
    company: Optional[str] = None
    notes: Optional[str] = None
    timezone: Optional[str] = None

@dataclass 
class CallResult:
    """Data class for call result tracking."""
    recipient: CallRecipient
    call_sid: str
    status: str
    initiated_at: datetime
    completed_at: Optional[datetime] = None
    duration: Optional[int] = None
    error: Optional[str] = None

class OutboundCaller:
    """Manages outbound calling functionality using Twilio and LiveKit."""
    
    def __init__(self):
        """Initialize the outbound caller with Twilio credentials."""
        self.twilio_client = None
        self.call_results: List[CallResult] = []
        
        # Load environment variables
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.twilio_phone_number = os.getenv('TWILIO_PHONE_NUMBER')
        self.livekit_api_key = os.getenv('LIVEKIT_API_KEY')
        self.livekit_api_secret = os.getenv('LIVEKIT_API_SECRET')
        self.livekit_url = os.getenv('LIVEKIT_URL')
        self.webhook_url = os.getenv('WEBHOOK_BASE_URL')  # Your server's webhook URL
        
        self._validate_credentials()
        self._initialize_twilio()

    def _validate_credentials(self):
        """Validate that all required credentials are present."""
        required_vars = [
            'TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_PHONE_NUMBER',
            'LIVEKIT_API_KEY', 'LIVEKIT_API_SECRET', 'LIVEKIT_URL', 'WEBHOOK_BASE_URL'
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    def _initialize_twilio(self):
        """Initialize the Twilio client."""
        try:
            self.twilio_client = Client(self.account_sid, self.auth_token)
            logger.info("Twilio client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Twilio client: {e}")
            raise

    def validate_phone_number(self, phone_number: str, default_region: str = "US") -> str:
        """
        Validate and format a phone number using phonenumbers library.
        
        Args:
            phone_number: The phone number to validate
            default_region: The default region code for parsing
            
        Returns:
            Formatted phone number in E164 format
            
        Raises:
            NumberParseException: If the number cannot be parsed or is invalid
        """
        try:
            parsed_number = phonenumbers.parse(phone_number, default_region)
            if not phonenumbers.is_valid_number(parsed_number):
                raise NumberParseException(NumberParseException.NOT_A_NUMBER, 
                                         "The provided number is not valid")
            return phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
        except NumberParseException as e:
            logger.error(f"Invalid phone number {phone_number}: {e}")
            raise

    async def make_outbound_call(self, recipient: CallRecipient) -> CallResult:
        """
        Make an outbound call to a recipient.
        
        Args:
            recipient: The CallRecipient object containing call details
            
        Returns:
            CallResult object with call information
        """
        logger.info(f"Initiating outbound call to {recipient.name} at {recipient.phone_number}")
        
        try:
            # Validate the phone number
            validated_number = self.validate_phone_number(recipient.phone_number)
            
            # Create a unique room name for this call
            room_name = f"outbound-call-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{recipient.name.replace(' ', '-').lower()}"
            
            # Construct the LiveKit SIP URI
            # This should point to your LiveKit SIP endpoint
            sip_uri = f"sip:{room_name}@{self.livekit_url.replace('wss://', '').replace('ws://', '')}"
            
            # Create the call using Twilio
            call = self.twilio_client.calls.create(
                to=validated_number,
                from_=self.twilio_phone_number,
                url=f"{self.webhook_url}/twiml/outbound",  # TwiML webhook endpoint
                status_callback=f"{self.webhook_url}/webhook/call-status",
                status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
                status_callback_method='POST',
                record=True,  # Optional: record the call
                machine_detection='Enable',  # Detect answering machines
                machine_detection_timeout=30,
                # Add custom parameters for your LiveKit integration
                send_digits='ww',  # Wait before proceeding
                timeout=60
            )
            
            # Create call result
            call_result = CallResult(
                recipient=recipient,
                call_sid=call.sid,
                status=call.status,
                initiated_at=datetime.now()
            )
            
            self.call_results.append(call_result)
            logger.info(f"Call initiated successfully. SID: {call.sid}")
            
            return call_result
            
        except (TwilioException, NumberParseException) as e:
            logger.error(f"Failed to make outbound call to {recipient.phone_number}: {e}")
            call_result = CallResult(
                recipient=recipient,
                call_sid="",
                status="failed",
                initiated_at=datetime.now(),
                error=str(e)
            )
            self.call_results.append(call_result)
            return call_result

    async def make_bulk_calls(self, recipients: List[CallRecipient], 
                            delay_between_calls: int = 30) -> List[CallResult]:
        """
        Make multiple outbound calls with delays between them.
        
        Args:
            recipients: List of CallRecipient objects
            delay_between_calls: Seconds to wait between calls
            
        Returns:
            List of CallResult objects
        """
        logger.info(f"Starting bulk calling campaign for {len(recipients)} recipients")
        results = []
        
        for i, recipient in enumerate(recipients):
            try:
                result = await self.make_outbound_call(recipient)
                results.append(result)
                
                # Add delay between calls (except for the last one)
                if i < len(recipients) - 1:
                    logger.info(f"Waiting {delay_between_calls} seconds before next call...")
                    await asyncio.sleep(delay_between_calls)
                    
            except Exception as e:
                logger.error(f"Error making call to {recipient.name}: {e}")
                error_result = CallResult(
                    recipient=recipient,
                    call_sid="",
                    status="error",
                    initiated_at=datetime.now(),
                    error=str(e)
                )
                results.append(error_result)
        
        logger.info(f"Bulk calling campaign completed. {len(results)} calls processed")
        return results

    def get_call_status(self, call_sid: str) -> Dict:
        """
        Get the current status of a call by SID.
        
        Args:
            call_sid: The Twilio call SID
            
        Returns:
            Dictionary with call details
        """
        try:
            call = self.twilio_client.calls(call_sid).fetch()
            return {
                'sid': call.sid,
                'status': call.status,
                'duration': call.duration,
                'start_time': call.start_time,
                'end_time': call.end_time,
                'from_': call.from_,
                'to': call.to
            }
        except TwilioException as e:
            logger.error(f"Failed to fetch call status for {call_sid}: {e}")
            return {'error': str(e)}

    def update_call_result(self, call_sid: str, status: str, 
                          duration: Optional[int] = None):
        """
        Update a call result with new status information.
        
        Args:
            call_sid: The Twilio call SID
            status: New status
            duration: Call duration in seconds
        """
        for result in self.call_results:
            if result.call_sid == call_sid:
                result.status = status
                if duration:
                    result.duration = duration
                if status in ['completed', 'failed', 'busy', 'no-answer']:
                    result.completed_at = datetime.now()
                break

    def get_campaign_summary(self) -> Dict:
        """
        Get a summary of all call results.
        
        Returns:
            Dictionary with campaign statistics
        """
        if not self.call_results:
            return {"message": "No calls made yet"}
        
        total_calls = len(self.call_results)
        status_counts = {}
        
        for result in self.call_results:
            status_counts[result.status] = status_counts.get(result.status, 0) + 1
        
        successful_calls = sum(1 for r in self.call_results if r.status == 'completed')
        success_rate = (successful_calls / total_calls) * 100 if total_calls > 0 else 0
        
        return {
            'total_calls': total_calls,
            'success_rate': f"{success_rate:.1f}%",
            'status_breakdown': status_counts,
            'successful_calls': successful_calls
        }


# Example usage and testing functions
async def example_single_call():
    """Example of making a single outbound call."""
    caller = OutboundCaller()
    
    recipient = CallRecipient(
        name="John Doe",
        phone_number="+1234567890",  # Replace with actual number for testing
        company="Test Company",
        notes="Demo call for AI voice agent"
    )
    
    result = await caller.make_outbound_call(recipient)
    logger.info(f"Call result: {result}")


async def example_bulk_calls():
    """Example of making bulk outbound calls."""
    caller = OutboundCaller()
    
    recipients = [
        CallRecipient("Alice Smith", "+1234567891", "Company A"),
        CallRecipient("Bob Johnson", "+1234567892", "Company B"),
        CallRecipient("Carol Brown", "+1234567893", "Company C"),
    ]
    
    results = await caller.make_bulk_calls(recipients, delay_between_calls=45)
    
    # Print summary
    summary = caller.get_campaign_summary()
    logger.info(f"Campaign Summary: {summary}")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run example (uncomment one of these)
    # asyncio.run(example_single_call())
    # asyncio.run(example_bulk_calls())
    
    logger.info("OutboundCaller module loaded successfully")
    logger.info("Please check the README for setup instructions and examples")
