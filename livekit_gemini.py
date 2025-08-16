import logging
import os
from system_prompt import system_prompt

from dotenv import load_dotenv
_ = load_dotenv(override=True)

logger = logging.getLogger("dlai-agent-gemini")
logger.setLevel(logging.INFO)

from livekit.agents import Agent, AgentSession, JobContext
from livekit.plugins import google, silero, deepgram


class Assistant(Agent):
    def __init__(self) -> None:
        llm = google.LLM(model="gemini-2.5-flash")

        dg_api_key = os.getenv("DEEPGRAM_API_KEY")
        if not dg_api_key:
            raise RuntimeError("DEEPGRAM_API_KEY is required for Deepgram STT/TTS")

        # Deepgram Nova-3 for STT
        stt = deepgram.STT(api_key=dg_api_key, model="nova-3")

        # Deepgram TTS with Aura-2 Asteria EN voice, 24kHz linear16
        tts = deepgram.TTS(
            api_key=dg_api_key,
            model="aura-2-asteria-en",
            sample_rate=24000,
            encoding="linear16",
        )

        vad = silero.VAD.load()

        super().__init__(
            instructions=system_prompt,
            stt=stt,
            llm=llm,
            tts=tts,
            vad=vad,
        )


async def entrypoint(ctx: JobContext):
    await ctx.connect()

    session = AgentSession()

    await session.start(
        room=ctx.room,
        agent=Assistant(),
    )


# Run directly: relies on LIVEKIT_* env vars for server connection
if __name__ == "__main__":
    from livekit.agents import WorkerOptions, cli

    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
