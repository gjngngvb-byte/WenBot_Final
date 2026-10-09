import json
import os
import time
from pathlib import Path

import requests
from openai import OpenAI

GRAPH_VERSION = os.environ.get("IG_GRAPH_VERSION", "v23.0")
ACCESS_TOKEN = os.environ.get("IG_ACCESS_TOKEN")
IG_USER_ID = os.environ.get("IG_USER_ID")
IG_USERNAME = (os.environ.get("IG_USERNAME") or "").lstrip("@").lower()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
TEXT_MODEL = os.environ.get("OPENAI_TEXT_MODEL", "gpt-4.1-mini")
STATE_FILE = Path("comentarios_respondidos.json")
BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"

if not ACCESS_TOKEN or not IG_USER_ID:
    raise SystemExit("IG_ACCESS_TOKEN e IG_USER_ID são necessários.")
if not OPENAI_API_KEY:
    raise SystemExit("OPENAI_API_KEY é necessária para redigir respostas.")

client = OpenAI(api_key=OPENAI_API_KEY)
try:
    state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
except (FileNotFoundError, json.JSONDecodeError):
    state = {"replied_ids": []}
replied = set(state.get("replied_ids", []))

def graph_get(path, params=None):
    query = dict(params or {})
    query["access_token"] = ACCESS_TOKEN
    response = requests.get(f"{BASE}/{path.lstrip('/')}", params=query, timeout=30)
    response.raise_for_status()
    return response.json()

def graph_post(path, data):
    payload = dict(data)
    payload["access_token"] = ACCESS_TOKEN
    response = requests.post(f"{BASE}/{path.lstrip('/')}", data=payload, timeout=30)
    response.raise_for_status()
    return response.json()

def criar_resposta(texto):
    prompt = f"""
Você é a pessoa responsável pelo perfil artístico Wen no Instagram.
Responda ao comentário abaixo em português brasileiro, de forma humana, breve e simpática.
Use no máximo duas frases, sem hashtags, sem fingir conhecer a pessoa e sem prometer algo.
Se o comentário for spam, golpe, propaganda ou contiver apenas insultos, responda exatamente: SKIP.
Comentário: {texto[:1000]}
"""
    response = client.responses.create(model=TEXT_MODEL, input=prompt)
    return (response.output_text or "").strip()

media_data = graph_get(f"{IG_USER_ID}/media", {
    "fields": "id,caption,timestamp,permalink",
    "limit": 20,
})
medias = media_data.get("data", [])
if not medias:
    print("Nenhuma publicação encontrada.")
    raise SystemExit(0)

# Mantém a publicação mais recente fora da fila, para responder aos posts anteriores.
for media in medias[1:]:
    media_id = media.get("id")
    if not media_id:
        continue
    try:
        comments_data = graph_get(f"{media_id}/comments", {
            "fields": "id,text,username,timestamp",
            "limit": 100,
        })
    except requests.HTTPError as exc:
        print(f"Não foi possível ler comentários da mídia {media_id}: {exc}")
        continue

    for comment in comments_data.get("data", []):
        comment_id = comment.get("id")
        text = (comment.get("text") or "").strip()
        username = (comment.get("username") or "").lower()
        if not comment_id or comment_id in replied or not text:
            continue
        if IG_USERNAME and username == IG_USERNAME:
            replied.add(comment_id)
            continue
        try:
            answer = criar_resposta(text)
            if not answer or answer.upper() == "SKIP":
                replied.add(comment_id)
                print(f"Comentário ignorado: {comment_id}")
                continue
            graph_post(f"{comment_id}/replies", {"message": answer})
            replied.add(comment_id)
            print(f"Respondido comentário {comment_id}")
            time.sleep(1)
        except Exception as exc:
            print(f"Falha ao responder comentário {comment_id}: {exc}")

STATE_FILE.write_text(json.dumps({"replied_ids": sorted(replied)}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
