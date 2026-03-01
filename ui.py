# ui.py
import gradio as gr
import uuid
from router_client.main import process_chat
from dotenv import load_dotenv

load_dotenv()

# Generate a unique thread ID for the current user's session
session_id = str(uuid.uuid4())

def respond(message, history):
    """
    Message: The current text the user typed.
    History: The previous chat history (handled automatically by Gradio).
    """
    # Send the message to the Router Client
    agent_response = process_chat(message, thread_id=session_id)
    return agent_response

demo = gr.ChatInterface(
    fn=respond,
    title="Automated Data Insights Desk",
    description="Ask me to query the local database or generate markdown reports!",
    type="messages" # Uses the newer messages format in Gradio
)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)