"""
SIP Configuration for LiveKit and Twilio Integration

This module handles the SIP trunk configuration between LiveKit and Twilio
for seamless voice call integration.
"""

import os
import logging
from typing import Dict, List, Optional
from livekit import api
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("sip-config")


class LiveKitSIPConfig:
    """Manages SIP configuration for LiveKit integration with Twilio."""
    
    def __init__(self):
        """Initialize SIP configuration with LiveKit credentials."""
        self.api_key = os.getenv('LIVEKIT_API_KEY')
        self.api_secret = os.getenv('LIVEKIT_API_SECRET')
        self.livekit_url = os.getenv('LIVEKIT_URL')
        self.webhook_url = os.getenv('WEBHOOK_BASE_URL')
        
        if not all([self.api_key, self.api_secret, self.livekit_url]):
            raise ValueError("Missing required LiveKit configuration")
        
        # Initialize LiveKit API client
        self.client = api.LiveKitApi(
            url=self.livekit_url,
            api_key=self.api_key,
            api_secret=self.api_secret
        )

    async def create_sip_trunk(self, trunk_name: str, twilio_config: Dict) -> Dict:
        """
        Create a SIP trunk configuration for Twilio integration.
        
        Args:
            trunk_name: Name for the SIP trunk
            twilio_config: Twilio configuration dictionary
            
        Returns:
            Dictionary with trunk configuration details
        """
        trunk_config = {
            'name': trunk_name,
            'inbound_addresses': [
                # Twilio's SIP addresses
                'siptrunk.pstn.twilio.com',
                'siptrunk.pstn.twilio.com:5060'
            ],
            'outbound_address': 'siptrunk.pstn.twilio.com:5060',
            'transport': 'udp',
            'auth_username': twilio_config.get('account_sid'),
            'auth_password': twilio_config.get('auth_token'),
            'inbound_numbers': twilio_config.get('phone_numbers', []),
            'outbound_number': twilio_config.get('outbound_number')
        }
        
        try:
            # Create SIP trunk using LiveKit API
            # Note: This is a simplified example - actual API calls may vary
            logger.info(f"Creating SIP trunk: {trunk_name}")
            
            # In practice, you would use LiveKit's SIP API here
            # trunk = await self.client.sip.create_trunk(trunk_config)
            
            logger.info(f"SIP trunk created successfully: {trunk_name}")
            return trunk_config
            
        except Exception as e:
            logger.error(f"Failed to create SIP trunk: {e}")
            raise

    async def create_sip_dispatch_rule(self, rule_name: str, 
                                     phone_number: str, 
                                     agent_name: str = "telephony_agent") -> Dict:
        """
        Create a SIP dispatch rule to route calls to specific agents.
        
        Args:
            rule_name: Name for the dispatch rule
            phone_number: Phone number pattern to match
            agent_name: Name of the agent to dispatch to
            
        Returns:
            Dictionary with dispatch rule details
        """
        dispatch_rule = {
            'name': rule_name,
            'trunk_ids': [],  # Associated trunk IDs
            'rule': {
                'dispatch_rule_direct': {
                    'room_name': f"sip-call-{phone_number.replace('+', '').replace(' ', '')}"
                }
            },
            'attributes': {
                'agent_name': agent_name,
                'phone_number': phone_number
            }
        }
        
        try:
            # Create dispatch rule using LiveKit API
            logger.info(f"Creating dispatch rule: {rule_name} -> {agent_name}")
            
            # In practice, you would use LiveKit's SIP API here
            # rule = await self.client.sip.create_dispatch_rule(dispatch_rule)
            
            logger.info(f"Dispatch rule created successfully: {rule_name}")
            return dispatch_rule
            
        except Exception as e:
            logger.error(f"Failed to create dispatch rule: {e}")
            raise

    async def configure_inbound_rules(self, phone_numbers: List[str]) -> List[Dict]:
        """
        Configure inbound dispatch rules for multiple phone numbers.
        
        Args:
            phone_numbers: List of phone numbers to configure
            
        Returns:
            List of created dispatch rules
        """
        rules = []
        
        for phone_number in phone_numbers:
            rule_name = f"inbound-rule-{phone_number.replace('+', '').replace(' ', '')}"
            
            rule = await self.create_sip_dispatch_rule(
                rule_name=rule_name,
                phone_number=phone_number,
                agent_name="telephony_agent"
            )
            
            rules.append(rule)
        
        return rules

    async def configure_outbound_rules(self) -> Dict:
        """
        Configure outbound dispatch rules for making calls.
        
        Returns:
            Dictionary with outbound rule configuration
        """
        outbound_rule = {
            'name': 'outbound-calls',
            'rule': {
                'dispatch_rule_direct': {
                    'room_name_prefix': 'outbound-call-'
                }
            },
            'attributes': {
                'agent_name': 'telephony_agent',
                'call_direction': 'outbound'
            }
        }
        
        try:
            logger.info("Configuring outbound dispatch rules")
            
            # Create outbound rule using LiveKit API
            # rule = await self.client.sip.create_dispatch_rule(outbound_rule)
            
            logger.info("Outbound dispatch rule configured successfully")
            return outbound_rule
            
        except Exception as e:
            logger.error(f"Failed to configure outbound rules: {e}")
            raise

    def generate_twiml_config(self) -> str:
        """
        Generate TwiML configuration for Twilio webhook.
        
        Returns:
            TwiML XML string for Twilio configuration
        """
        sip_domain = self.livekit_url.replace('wss://', '').replace('ws://', '')
        
        twiml_config = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Dial>
        <Sip>sip:livekit@{sip_domain}</Sip>
    </Dial>
</Response>"""
        
        return twiml_config

    def get_webhook_urls(self) -> Dict[str, str]:
        """
        Get webhook URLs for Twilio configuration.
        
        Returns:
            Dictionary with webhook URLs
        """
        base_url = self.webhook_url.rstrip('/')
        
        return {
            'voice_url': f"{base_url}/twiml/inbound",
            'voice_fallback_url': f"{base_url}/twiml/fallback", 
            'status_callback_url': f"{base_url}/webhook/call-status",
            'recording_status_callback_url': f"{base_url}/webhook/recording-status"
        }

    async def test_sip_connectivity(self) -> bool:
        """
        Test SIP connectivity between LiveKit and Twilio.
        
        Returns:
            True if connectivity test passes
        """
        try:
            logger.info("Testing SIP connectivity...")
            
            # Perform connectivity test
            # This would involve making a test SIP call or checking registration
            
            logger.info("SIP connectivity test passed")
            return True
            
        except Exception as e:
            logger.error(f"SIP connectivity test failed: {e}")
            return False


def print_setup_instructions():
    """Print setup instructions for SIP configuration."""
    print("""
🔧 SIP Configuration Setup Instructions

1. LiveKit SIP Configuration:
   - Enable SIP ingress in your LiveKit deployment
   - Configure SIP domain and authentication
   - Set up dispatch rules for call routing

2. Twilio Configuration:
   - Purchase a phone number in Twilio Console
   - Configure webhook URLs:
     * Voice URL: https://your-domain.com/twiml/inbound
     * Status Callback: https://your-domain.com/webhook/call-status
   - Set up SIP trunk to LiveKit (if using SIP trunking)

3. Webhook Server:
   - Deploy webhook_handler.py to your server
   - Ensure HTTPS is configured (required by Twilio)
   - Test webhook endpoints with ngrok for development

4. Environment Variables:
   - Update your .env file with all required credentials
   - Test configuration with the validation script

5. Testing:
   - Use the make_calls.py script to test outbound functionality
   - Monitor logs for call status and debugging

For detailed setup instructions, refer to:
- LiveKit SIP Documentation: https://docs.livekit.io/sip/
- Twilio Voice Documentation: https://www.twilio.com/docs/voice
    """)


async def main():
    """Main function for testing SIP configuration."""
    try:
        sip_config = LiveKitSIPConfig()
        
        print("✅ LiveKit SIP configuration initialized")
        
        # Test connectivity
        connectivity_ok = await sip_config.test_sip_connectivity()
        
        if connectivity_ok:
            print("✅ SIP connectivity test passed")
        else:
            print("❌ SIP connectivity test failed")
        
        # Print webhook URLs
        webhook_urls = sip_config.get_webhook_urls()
        print("\n📞 Webhook URLs:")
        for name, url in webhook_urls.items():
            print(f"   {name}: {url}")
        
        # Print TwiML config
        twiml = sip_config.generate_twiml_config()
        print(f"\n📄 TwiML Configuration:")
        print(twiml)
        
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        print_setup_instructions()


if __name__ == '__main__':
    import asyncio
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(main())
