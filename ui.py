import gradio as gr
import uuid
from router_client.main import process_chat

async def respond(message, chat_history):

    agent_response = await process_chat(message, thread_id=uuid.uuid4())

    chat_history.append(
        {"role": "user", "content": message}
    )

    chat_history.append(
        {"role": "assistant", "content": agent_response}
    )

    return "", chat_history


with gr.Blocks(title="A2A Automated Insights Desk") as demo:

    gr.Markdown("# 🤖 A2A Automated Insights Desk")

    chatbot = gr.Chatbot(height=500, value=[])

    with gr.Row():
        msg = gr.Textbox(placeholder="Ask a question...", container=False, scale=7)
        submit_btn = gr.Button("Submit", scale=1)

    clear = gr.ClearButton([msg, chatbot])

    msg.submit(respond, [msg, chatbot], [msg, chatbot])  # pylint: disable=no-member
    submit_btn.click(respond, [msg, chatbot], [msg, chatbot])  # pylint: disable=no-member


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)