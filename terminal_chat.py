import asyncio
import uuid

from router_client.main import process_chat
from observability.langfuse_client import langfuse


async def chat_loop():

    print("\n🤖 Automated Insights Desk (Terminal)")
    print("Type 'exit' to quit.\n")

    thread_id = str(uuid.uuid4())

    while True:

        user_input = input("You: ")

        if user_input.lower() in ["exit", "quit"]:
            print("Goodbye 👋")
            break

        try:

            response = await process_chat(user_input, thread_id)

            print("\nAssistant:")
            print(response)
            print("\n" + "-" * 60 + "\n")

        except Exception as e:

            print("\n⚠️ Error occurred:")
            print(str(e))
            print("\n")

    # IMPORTANT: flush traces before exit
    langfuse.flush()


if __name__ == "__main__":
    asyncio.run(chat_loop())