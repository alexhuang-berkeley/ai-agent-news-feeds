# AI Agent News Feeds

This repository contains a simple Python script that emails you the latest news and academic papers for a topic of interest.

## Requirements

- Python 3.8+
- Packages: `feedparser`, `arxiv`, `schedule`, `openai`, `gradio`

Install the required packages:

```bash
pip install feedparser arxiv schedule openai gradio
```

## Usage

Run the agent:

```bash
python news_agent.py
```

The first run will prompt for:

1. Keywords or topics of interest
2. Cadence in minutes between updates
3. Email credentials and recipient address
4. SMTP server information

The configuration is stored in `config.json`. The agent will run continuously and send updates at the chosen cadence. Stop with `Ctrl+C`.

## Browser-Based Interface

Save your OpenAI API key in a file named `openai_key.txt` (or set the
`OPENAI_API_KEY` environment variable) and launch the conversational UI:

```bash
# Optionally set the key via environment variable instead of the file
export OPENAI_API_KEY=your-key
python agent_ui.py
```

The UI opens a chat where the agent explains its purpose, asks for your topics of interest, refines keywords via OpenAI, collects cadence and email settings, and finally confirms before starting the news feed agent.
