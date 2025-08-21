import asyncio
from dotenv import load_dotenv
from livekit import api

# lk dispatch create --new-room --agent-name outbound-caller --metadata '+918779536074'

room_name = "outbound-caller-room"
agent_name = "outbound-caller"

# load env variables
load_dotenv()

async def create_explicit_dispatch(phone_number):
    lkapi = api.LiveKitAPI()
    dispatch = await lkapi.agent_dispatch.create_dispatch(
        api.CreateAgentDispatchRequest(
            agent_name=agent_name, room=room_name, metadata=phone_number
        )
    )
    print("created dispatch", dispatch)

    dispatches = await lkapi.agent_dispatch.list_dispatch(room_name=room_name)
    print(f"there are {len(dispatches)} dispatches in {room_name}")
    await lkapi.aclose()

# Example usage (commented out for module import)
# if __name__ == "__main__":
#     asyncio.run(create_explicit_dispatch("+918779536074"))