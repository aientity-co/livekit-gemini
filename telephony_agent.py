import asyncio
import logging
import sys
from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
    function_tool
)
from livekit.plugins import deepgram, google, cartesia, silero
from system_prompt import system_prompt

load_dotenv()
logger = logging.getLogger("telephony-agent")

@function_tool
async def get_current_time() -> str:
    """Get the current time."""
    from datetime import datetime
    return f"The current time is {datetime.now().strftime('%I:%M %p')}"

async def entrypoint(ctx: JobContext):
    """Main entry point for the telephony voice agent."""
    await ctx.connect()
    
    # Wait for participant (caller) to join
    participant = await ctx.wait_for_participant()
    logger.info(f"Phone call connected from participant: {participant.identity}")
    
    # Initialize the conversational agent
    agent = Agent(
        instructions=system_prompt,
        tools=[get_current_time]
    )
    
    # Configure the voice processing pipeline optimized for telephony
    session = AgentSession(
        # Voice Activity Detection
        vad=silero.VAD.load(),
        
        # Speech-to-Text - Deepgram Nova-3
        stt=deepgram.STT(
            model="nova-3",  # Latest model
            language="en-US",
            interim_results=True,
            punctuate=True,
            smart_format=True,
            filler_words=True,
            endpointing_ms=25,
            sample_rate=16000
        ),
        
        # Large Language Model - GPT-4o-mini
        llm=google.LLM(
            model="gemini-2.5-flash",
            temperature=0.7
        ),
        
        # Text-to-Speech - Cartesia Sonic-2
        tts=cartesia.TTS(
            model="sonic-2",
            voice="78ab82d5-25be-4f7d-82b3-7ad64e5b85b2",  # Professional female voice
            language="en",
            speed=1.0,
            sample_rate=24000
        )
    )
    
    # Start the agent session
    await session.start(agent=agent, room=ctx.room)
    
    # Generate personalized greeting based on time of day
    import datetime
    hour = datetime.datetime.now().hour
    if hour < 12:
        time_greeting = "Good morning"
    elif hour < 18:
        time_greeting = "Good afternoon"
    else:
        time_greeting = "Good evening"
    
    await session.generate_reply(
        instructions=f"""Say '{time_greeting}! Thank you for calling. Whats happening?'
        Speak warmly and professionally at a moderate pace."""
    )

if __name__ == "__main__":
    # Configure logging for better debugging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the agent with the name that matches your dispatch rule
    cli.run_app(WorkerOptions(
        entrypoint_fnc=entrypoint,
        agent_name="telephony_agent"  # This must match your dispatch rule
    ))