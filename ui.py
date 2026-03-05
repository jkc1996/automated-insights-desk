print("UI FILE STARTED")

import gradio as gr
import uuid
from router_client.main import process_chat


async def respond(message, chat_history):

    thread_id = str(uuid.uuid4())

    agent_response = await process_chat(message, thread_id)

    chat_history.append({"role": "user", "content": message})
    chat_history.append({"role": "assistant", "content": agent_response})

    return "", chat_history


with gr.Blocks(title="A2A Automated Insights Desk") as demo:

    gr.Markdown("# 🤖 A2A Automated Insights Desk")

    chatbot = gr.Chatbot(height=500)

    with gr.Row():
        msg = gr.Textbox(placeholder="Ask a question...", scale=7)
        submit_btn = gr.Button("Submit", scale=1)

    clear = gr.ClearButton([msg, chatbot])

    msg.submit(respond, [msg, chatbot], [msg, chatbot])
    submit_btn.click(respond, [msg, chatbot], [msg, chatbot])


if __name__ == "__main__":
    print("Launching Gradio UI...")

    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        ssl_verify=False
    )