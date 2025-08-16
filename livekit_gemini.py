import logging
import os

from dotenv import load_dotenv
_ = load_dotenv(override=True)

logger = logging.getLogger("dlai-agent-gemini")
logger.setLevel(logging.INFO)

from livekit.agents import Agent, AgentSession, JobContext
from livekit.plugins import google, silero


class Assistant(Agent):
    def __init__(self) -> None:
        llm = google.LLM(model="gemini-1.5-flash")

        creds_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        stt = google.STT(credentials_file=creds_file) if creds_file else google.STT()
        tts = google.TTS(credentials_file=creds_file) if creds_file else google.TTS()
        vad = silero.VAD.load()

        super().__init__(
            instructions="""
                You are a helpful assistant communicating
                via voice
            """,
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
