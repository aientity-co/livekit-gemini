import asyncio
import logging
from dotenv import load_dotenv
import json
import os
from time import perf_counter
from typing import Annotated
from livekit import rtc, api
from livekit.agents import (
    Agent,
    AgentSession,
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    llm,
)
from livekit.agents.voice import SpeechHandle
from livekit.plugins import deepgram, google, cartesia, silero
from system_prompt import system_prompt

# load environment variables, this is optional, only used for local development
load_dotenv(dotenv_path=".env.local")
logger = logging.getLogger("outbound-caller")
logger.setLevel(logging.INFO)

outbound_trunk_id = os.getenv("SIP_OUTBOUND_TRUNK_ID")
_default_instructions = system_prompt


async def entrypoint(ctx: JobContext):
    global _default_instructions, outbound_trunk_id
    logger.info(f"connecting to room {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    user_identity = "phone_user"
    # the phone number to dial is provided in the job metadata
    phone_number = ctx.job.metadata
    logger.info(f"dialing {phone_number} to room {ctx.room.name}")

    # look up the user's phone number and appointment details
    instructions = (
        _default_instructions
        + "Customer's name is Krunal, he is a seller on india mart"
    )

    # `create_sip_participant` starts dialing the user
    await ctx.api.sip.create_sip_participant(
        api.CreateSIPParticipantRequest(
            room_name=ctx.room.name,
            sip_trunk_id=outbound_trunk_id,
            sip_call_to=phone_number,
            participant_identity=user_identity,
        )
    )

    # a participant is created as soon as we start dialing
    participant = await ctx.wait_for_participant(identity=user_identity)

    # wait for pickup before starting the agent so the greeting is heard
    logger.info("waiting for user to pick up...")
    start_time = perf_counter()
    picked_up = False
    while perf_counter() - start_time < 60:
        call_status = participant.attributes.get("sip.callStatus")
        if call_status == "active":
            logger.info("user has picked up")
            picked_up = True
            break
        if participant.disconnect_reason == rtc.DisconnectReason.USER_REJECTED:
            logger.info("user rejected the call, exiting job")
            ctx.shutdown()
            return
        if participant.disconnect_reason == rtc.DisconnectReason.USER_UNAVAILABLE:
            logger.info("user did not pick up, exiting job")
            ctx.shutdown()
            return
        await asyncio.sleep(0.2)

    if not picked_up:
        logger.info("pickup timed out, exiting job")
        ctx.shutdown()
        return

    # start the agent once the call is active
    await run_voice_pipeline_agent(ctx, participant, instructions)


class CallAgent(Agent):
    """
    Agent with call-specific functions
    """

    def __init__(self, api: api.LiveKitAPI, participant: rtc.RemoteParticipant, room: rtc.Room, instructions: str):
        self.api = api
        self.participant = participant
        self.room = room
        
        cartesia_voice_id = os.getenv("CARTESIA_VOICE_ID")


        logger.info("Using Deepgram STT")
        stt_impl = deepgram.STT(
            model="nova-3",
            language="en-US",
            interim_results=True,
            punctuate=True,
            smart_format=True,
            filler_words=True,
            endpointing_ms=25,
            sample_rate=16000,
        )

        logger.info("Using Cartesia TTS")
        tts_impl = cartesia.TTS(
            model="sonic-2",
            voice=cartesia_voice_id,
            language="en",
            speed=1.0,
            sample_rate=24000,
        )

        super().__init__(
            instructions=instructions,
            vad=silero.VAD.load(),
            stt=stt_impl,
            llm=google.LLM(model="gemini-2.5-flash", temperature=0.7),
            tts=tts_impl,
        )

    async def hangup(self):
        try:
            await self.api.room.remove_participant(
                api.RoomParticipantIdentity(
                    room=self.room.name,
                    identity=self.participant.identity,
                )
            )
        except Exception as e:
            # it's possible that the user has already hung up, this error can be ignored
            logger.info(f"received error while ending call: {e}")

    @llm.function_tool()
    async def end_call(self):
        """Called when the user wants to end the call"""
        logger.info(f"ending the call for {self.participant.identity}")
        await self.hangup()

    @llm.function_tool()
    async def look_up_availability(
        self,
        date: Annotated[str, "The date of the appointment to check availability for"],
    ):
        """Called when the user asks about alternative appointment availability"""
        logger.info(
            f"looking up availability for {self.participant.identity} on {date}"
        )
        await asyncio.sleep(3)
        return json.dumps(
            {
                "available_times": ["1pm", "2pm", "3pm"],
            }
        )

    @llm.function_tool()
    async def confirm_appointment(
        self,
        date: Annotated[str, "date of the appointment"],
        time: Annotated[str, "time of the appointment"],
    ):
        """Called when the user confirms their appointment on a specific date. Use this tool only when they are certain about the date and time."""
        logger.info(
            f"confirming appointment for {self.participant.identity} on {date} at {time}"
        )
        return "reservation confirmed"

    @llm.function_tool()
    async def detected_answering_machine(self):
        """Called when the call reaches voicemail. Use this tool AFTER you hear the voicemail greeting"""
        logger.info(f"detected answering machine for {self.participant.identity}")
        await self.hangup()


async def run_voice_pipeline_agent(
    ctx: JobContext, participant: rtc.RemoteParticipant, instructions: str
):
    logger.info("starting voice pipeline agent")

    # Create agent with call-specific functions
    agent = CallAgent(
        api=ctx.api,
        participant=participant,
        room=ctx.room,
        instructions=instructions
    )
    
    # Start agent session
    session = AgentSession()
    await session.start(agent, room=ctx.room)

    # greet to verify TTS path after pickup
    try:
        await session.say("Hi, this is the scheduling assistant. I'm on the line now. How can I help you today?")
    except Exception as e:
        logger.info(f"failed to send greeting: {e}")


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


if __name__ == "__main__":
    if not outbound_trunk_id or not outbound_trunk_id.startswith("ST_"):
        raise ValueError(
            "SIP_OUTBOUND_TRUNK_ID is not set"
        )
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            # giving this agent a name will allow us to dispatch it via API
            # automatic dispatch is disabled when `agent_name` is set
            agent_name="outbound-caller",
            # prewarm by loading the VAD model, needed only for VoicePipelineAgent
            prewarm_fnc=prewarm,
        )
    )