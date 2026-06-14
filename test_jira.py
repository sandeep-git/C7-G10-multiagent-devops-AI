"""Quick test to verify Jira credentials are working."""
import os, base64, json, urllib.request, urllib.error
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

base_url = os.getenv("JIRA_BASE_URL", "").rstrip("/")
email    = os.getenv("JIRA_EMAIL", "")
token    = os.getenv("JIRA_API_TOKEN", "")
project  = os.getenv("JIRA_PROJECT_KEY", "")

print("Testing Jira connection...")
print(f"  URL     : {base_url}")
print(f"  Email   : {email}")
print(f"  Project : {project}")
print(f"  Token   : {'*' * (len(token)-4) + token[-4:] if token else 'NOT SET'}")
print()

if "your-" in email or "your-" in token:
    print("❌ Please fill in JIRA_EMAIL and JIRA_API_TOKEN in .env first.")
    exit(1)

creds = base64.b64encode(f"{email}:{token}".encode()).decode()
headers = {"Authorization": f"Basic {creds}", "Accept": "application/json"}

# Test 1: Check user auth
try:
    req = urllib.request.Request(f"{base_url}/rest/api/3/myself", headers=headers)
    resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
    print(f"✅ Auth OK — Connected as: {resp['displayName']} ({resp['emailAddress']})")
except urllib.error.HTTPError as e:
    print(f"❌ Auth failed ({e.code}): {e.read().decode()}")
    exit(1)

# Test 2: Check project exists
try:
    req = urllib.request.Request(f"{base_url}/rest/api/3/project/{project}", headers=headers)
    resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
    print(f"✅ Project OK — '{resp['name']}' (key: {resp['key']})")
except urllib.error.HTTPError as e:
    print(f"❌ Project '{project}' not found ({e.code}) — check JIRA_PROJECT_KEY in .env")
    exit(1)

print()
print("🎉 All checks passed! Jira is ready.")
print(f"   Tickets will be created at: {base_url}/browse/{project}-XXXX")
