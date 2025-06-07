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

SYSTEM_PROMPT = (
    "You are a news feed setup assistant. Collect the user's search keywords, "
    "cadence in minutes, sender email, sender password, recipient email, SMTP "
    "server and SMTP port. Suggest improved keywords after the user provides "
    "initial topics. After gathering all details, summarize them and ask for "
    "yes/no confirmation to start the agent."
)


def ai_response(messages):
    if not openai.api_key:
        return "OPENAI_API_KEY not set"
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
    messages = state.get("messages", [])
    info = state.get("info", {})
    step = state.get("step", 0)

    messages.append({"role": "user", "content": user_message})

    if step == 0:
        info["keywords"] = user_message
        messages.append({
            "role": "system",
            "content": (
                f"The user is interested in: {user_message}. Suggest improved "
                "keywords as a comma-separated list and ask for confirmation "
                "or modifications."
            ),
        })
        response = ai_response(messages)
        messages.append({"role": "assistant", "content": response})
        state["step"] = 1
    elif step == 1:
        info["keywords"] = user_message.strip()
        messages.append({"role": "system", "content": "Acknowledge and ask for the update cadence in minutes."})
        response = ai_response(messages)
        messages.append({"role": "assistant", "content": response})
        state["step"] = 2
    elif step == 2:
        try:
            info["cadence_minutes"] = int(user_message)
            messages.append({"role": "system", "content": "Ask for the sender email address."})
            response = ai_response(messages)
            state["step"] = 3
        except ValueError:
            messages.append({"role": "system", "content": "Inform the user the cadence must be a number."})
            response = ai_response(messages)
        messages.append({"role": "assistant", "content": response})
    elif step == 3:
        info["sender_email"] = user_message
        messages.append({"role": "system", "content": "Ask for the sender email password. Mention it will be stored locally."})
        response = ai_response(messages)
        messages.append({"role": "assistant", "content": response})
        state["step"] = 4
    elif step == 4:
        info["sender_password"] = user_message
        messages.append({"role": "system", "content": "Ask for the recipient email address."})
        response = ai_response(messages)
        messages.append({"role": "assistant", "content": response})
        state["step"] = 5
    elif step == 5:
        info["recipient_email"] = user_message
        messages.append({"role": "system", "content": "Ask for the SMTP server (e.g., smtp.gmail.com)."})
        response = ai_response(messages)
        messages.append({"role": "assistant", "content": response})
        state["step"] = 6
    elif step == 6:
        info["smtp_server"] = user_message
        messages.append({"role": "system", "content": "Ask for the SMTP port (e.g., 587)."})
        response = ai_response(messages)
        messages.append({"role": "assistant", "content": response})
        state["step"] = 7
    elif step == 7:
        try:
            info["smtp_port"] = int(user_message)
            summary = (
                f"Confirm the following settings:\nKeywords: {info['keywords']}\n"
                f"Cadence: {info['cadence_minutes']} minutes\n"
                f"Sender: {info['sender_email']}\n"
                f"Recipient: {info['recipient_email']}\n"
                f"SMTP: {info['smtp_server']}:{info['smtp_port']}\n"
                "Reply yes to start or no to cancel."
            )
            messages.append({"role": "system", "content": summary})
            response = ai_response(messages)
            state["step"] = 8
        except ValueError:
            messages.append({"role": "system", "content": "Tell the user the SMTP port must be numeric."})
            response = ai_response(messages)
        messages.append({"role": "assistant", "content": response})
    elif step == 8:
        if user_message.strip().lower().startswith("y"):
            start_agent({
                "keywords": info["keywords"],
                "cadence_minutes": info["cadence_minutes"],
                "sender_email": info["sender_email"],
                "sender_password": info["sender_password"],
                "recipient_email": info["recipient_email"],
                "smtp_server": info["smtp_server"],
                "smtp_port": info["smtp_port"],
            })
            messages.append({"role": "system", "content": "Inform the user that the agent has started."})
        else:
            messages.append({"role": "system", "content": "Inform the user that setup has been canceled."})
        response = ai_response(messages)
        messages.append({"role": "assistant", "content": response})
        state["step"] = 9
    else:
        messages.append({"role": "system", "content": "Politely say the setup is complete."})
        response = ai_response(messages)
        messages.append({"role": "assistant", "content": response})

    history.append((user_message, response))
    state.update({"messages": messages, "info": info})
    return history, state, ""


def init_chat():
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "Begin setup."},
    ]
    first = ai_response(messages)
    messages.append({"role": "assistant", "content": first})
    state = {"step": 0, "messages": messages, "info": {}}
    return [(None, first)], state, ""


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
