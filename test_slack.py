"""Quick test to verify Slack webhook is working."""
import os, json, urllib.request, urllib.error
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")
channel     = os.getenv("SLACK_CHANNEL", "#incidents")

print("Testing Slack connection...")
print(f"  Webhook : {webhook_url[:50]}..." if len(webhook_url) > 50 else f"  Webhook : {webhook_url}")
print(f"  Channel : {channel}")
print()

if not webhook_url or "YOUR/WEBHOOK" in webhook_url:
    print("❌ SLACK_WEBHOOK_URL not set in .env")
    print("   Get it from: https://api.slack.com/apps → Incoming Webhooks → Add Webhook")
    exit(1)

# Send a test message
payload = {
    "text": "✅ DevOps Incident Suite — Slack integration test successful!",
    "blocks": [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "🚨 DevOps Incident Suite — Test Message"}
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "✅ *Slack integration is working correctly!*\nThis is a test message from your DevOps Incident Analysis Suite.\nReal incident alerts will appear here after pipeline approval."
            }
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Channel:*\n{channel}"},
                {"type": "mrkdwn", "text": "*Status:*\n:white_check_mark: Connected"},
            ]
        }
    ]
}

data = json.dumps(payload).encode()
req = urllib.request.Request(
    webhook_url,
    data=data,
    headers={"Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = resp.read().decode()
        if result == "ok":
            print(f"✅ Slack webhook working! Test message sent to {channel}")
            print("   Check your Slack channel for the test message.")
        else:
            print(f"⚠️  Unexpected response: {result}")
except urllib.error.HTTPError as e:
    error = e.read().decode()
    print(f"❌ Slack error ({e.code}): {error}")
    if e.code == 403:
        print("   → Webhook URL is invalid or revoked. Regenerate it in api.slack.com/apps")
    elif e.code == 404:
        print("   → Channel not found. Check SLACK_CHANNEL in .env")
