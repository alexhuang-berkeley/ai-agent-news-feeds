import json
import time
from pathlib import Path
import feedparser
import arxiv
import schedule
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

CONFIG_FILE = Path('config.json')

def setup():
    keywords = input('Enter keywords or topics of interest (comma separated): ').strip()
    confirm = input(f'Use these keywords? {keywords} (y/n): ').strip().lower()
    if confirm != 'y':
        keywords = input('Enter desired keywords: ').strip()
    cadence_minutes = int(input('Enter update cadence in minutes: ').strip())
    sender_email = input('Enter sender email address: ').strip()
    sender_password = input('Enter sender email password (will be stored locally): ').strip()
    recipient_email = input('Enter recipient email address: ').strip()
    smtp_server = input('Enter SMTP server (e.g., smtp.gmail.com): ').strip()
    smtp_port = int(input('Enter SMTP port (e.g., 587): ').strip())

    config = {
        'keywords': keywords,
        'cadence_minutes': cadence_minutes,
        'sender_email': sender_email,
        'sender_password': sender_password,
        'recipient_email': recipient_email,
        'smtp_server': smtp_server,
        'smtp_port': smtp_port,
    }
    CONFIG_FILE.write_text(json.dumps(config, indent=2))
    return config


def load_config():
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return setup()


def fetch_news(keywords):
    query = '+'.join(keywords.split())
    url = f'https://news.google.com/rss/search?q={query}'
    feed = feedparser.parse(url)
    entries = feed.entries[:5]
    news_items = [f"{e.title} - {e.link}" for e in entries]
    return news_items


def fetch_arxiv_papers(keywords):
    search = arxiv.Search(query=keywords, max_results=5, sort_by=arxiv.SortCriterion.SubmittedDate)
    papers = [f"{result.title} - {result.entry_id}" for result in search.results()]
    return papers


def compose_email(news_items, papers, config):
    body = 'Latest News:\n' + '\n'.join(news_items) + '\n\nLatest Papers:\n' + '\n'.join(papers)
    msg = MIMEMultipart()
    msg['Subject'] = f"News Update for {config['keywords']}"
    msg['From'] = config['sender_email']
    msg['To'] = config['recipient_email']
    msg.attach(MIMEText(body, 'plain'))
    return msg


def send_email(message, config):
    with smtplib.SMTP(config['smtp_server'], config['smtp_port']) as server:
        server.starttls()
        server.login(config['sender_email'], config['sender_password'])
        server.sendmail(config['sender_email'], config['recipient_email'], message.as_string())


def job(config):
    news_items = fetch_news(config['keywords'])
    papers = fetch_arxiv_papers(config['keywords'])
    msg = compose_email(news_items, papers, config)
    send_email(msg, config)
    print('Update sent.')


def main():
    config = load_config()
    schedule.every(config['cadence_minutes']).minutes.do(job, config)
    print('Agent started. Press Ctrl+C to stop.')
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    main()
