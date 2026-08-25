from pathlib import Path

path = Path("backend/.env")
text = path.read_text(encoding="utf-8")
lines = text.splitlines()
new_lines = []
for line in lines:
    if line.startswith("FIREBASE_CREDENTIALS_FILE="):
        new_lines.append("FIREBASE_CREDENTIALS_FILE=C:/Users/RAVIKANTH/Downloads/trading-ai-bot-d3e16-firebase-adminsdk-fbsvc-2b07665cdb.json")
    elif line.startswith("FIREBASE_CREDENTIALS_JSON="):
        new_lines.append("FIREBASE_CREDENTIALS_JSON=")
    else:
        new_lines.append(line)
path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
print("updated")
