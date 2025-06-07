import os
import json
import threading
from pathlib import Path

import gradio as gr
import openai

from news_agent import main as run_news_agent

CONFIG_FILE = Path("config.json")
KEY_FILE = Path("openai_key.txt")
if KEY_FILE.exists():
    openai.api_key = KEY_FILE.read_text().strip()
else:
    openai.api_key = os.getenv("OPENAI_API_KEY")

intro = (
    "Hello! I'm your News Feed AI Agent. I can send you regular emails with "
    "the latest news articles and academic papers based on your interests. "
    "Let's set things up. What topics are you interested in?"
)


def refine_keywords(keywords: str) -> str:
    """Use OpenAI to suggest improved search keywords."""
    if not openai.api_key:
        return "OPENAI_API_KEY not set"
    prompt = (
        "Suggest refined keywords for searching news and academic papers based on: "
        f"{keywords}. Provide a comma-separated list of improved keywords."
    )
    messages = [
        {"role": "system", "content": "You help refine search keywords."},
        {"role": "user", "content": prompt},
    ]
    try:
        resp = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)
        return resp.choices[0].message["content"].strip()
    except Exception as e:
        return str(e)


def start_agent(config: dict) -> None:
    """Write config and launch the news agent in a background thread."""
    CONFIG_FILE.write_text(json.dumps(config, indent=2))
    thread = threading.Thread(target=run_news_agent, daemon=True)
    thread.start()


def chat(user_message: str, history: list, state: dict):
    step = state.get("step", 0)
    response = ""

    if step == 0:
        state["keywords"] = user_message
        suggestions = refine_keywords(user_message)
        response = (
            f"Here are some suggested keywords:\n{suggestions}\n"
            "You can modify them or keep your original ones."
        )
        state["step"] = 1
    elif step == 1:
        # user may provide new keywords or accept suggestions
        if user_message.strip():
            state["keywords"] = user_message.strip()
        response = "How often in minutes should I send updates?"
        state["step"] = 2
    elif step == 2:
        try:
            state["cadence_minutes"] = int(user_message)
            response = "What's the sender email address?"
            state["step"] = 3
        except ValueError:
            response = "Please provide a number for the cadence in minutes."
    elif step == 3:
        state["sender_email"] = user_message
        response = "Sender email password (will be stored locally):"
        state["step"] = 4
    elif step == 4:
        state["sender_password"] = user_message
        response = "Recipient email address:"
        state["step"] = 5
    elif step == 5:
        state["recipient_email"] = user_message
        response = "SMTP server (e.g., smtp.gmail.com):"
        state["step"] = 6
    elif step == 6:
        state["smtp_server"] = user_message
        response = "SMTP port (e.g., 587):"
        state["step"] = 7
    elif step == 7:
        try:
            state["smtp_port"] = int(user_message)
            summary = (
                "Great! I will use the following settings:\n"
                f"Keywords: {state['keywords']}\n"
                f"Cadence: {state['cadence_minutes']} minutes\n"
                f"Sender: {state['sender_email']}\n"
                f"Recipient: {state['recipient_email']}\n"
                f"SMTP: {state['smtp_server']}:{state['smtp_port']}\n"
                "Type 'yes' to confirm and start the agent, or 'no' to cancel."
            )
            response = summary
            state["step"] = 8
        except ValueError:
            response = "Please provide a numeric SMTP port."
    elif step == 8:
        if user_message.lower().startswith("y"):
            start_agent({
                "keywords": state["keywords"],
                "cadence_minutes": state["cadence_minutes"],
                "sender_email": state["sender_email"],
                "sender_password": state["sender_password"],
                "recipient_email": state["recipient_email"],
                "smtp_server": state["smtp_server"],
                "smtp_port": state["smtp_port"],
            })
            response = "Agent started with provided configuration."
            state["step"] = 9
        else:
            response = "Setup canceled."
            state["step"] = 9
    else:
        response = "Setup complete."

    history.append((user_message, response))
    return history, state, ""


def init_chat():
    return [(None, intro)], {"step": 0}, ""


with gr.Blocks() as demo:
    gr.Markdown("# News Feed AI Agent")
    chatbot = gr.Chatbot()
    msg = gr.Textbox(label="Message")
    state = gr.State()
    send = gr.Button("Send")

    demo.load(init_chat, outputs=[chatbot, state, msg])
    send.click(chat, inputs=[msg, chatbot, state], outputs=[chatbot, state, msg])

if __name__ == "__main__":
    demo.launch()
