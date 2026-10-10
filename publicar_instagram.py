import os
import time
from urllib.parse import quote

import requests

GRAPH_VERSION = os.environ.get("IG_GRAPH_VERSION", "v23.0")
ACCESS_TOKEN = os.environ.get("IG_ACCESS_TOKEN")
IG_USER_ID = os.environ.get("IG_USER_ID")
IMAGE_URL_BASE = "https://gjngngvb-byte.github.io/WenBot_Final/wen_art.jpg"
CAPTION_FILE = "wen_art.txt"
BASE_URL = f"https://graph.facebook.com/{GRAPH_VERSION}"

def fail_for_response(response):
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        try:
            details = response.json().get("error", {})
            message = details.get("message", response.text[:500])
            code = details.get("code")
            raise RuntimeError(f"Instagram Graph API erro {code}: {message}") from exc
        except ValueError:
            raise RuntimeError(f"Instagram Graph API respondeu HTTP {response.status_code}: {response.text[:500]}") from exc

def main():
    if not ACCESS_TOKEN or not IG_USER_ID:
        raise SystemExit(
            "Publicação direta exige os Secrets IG_ACCESS_TOKEN e IG_USER_ID. "
            "Configure-os em GitHub → Settings → Secrets and variables → Actions."
        )

    with open(CAPTION_FILE, "r", encoding="utf-8") as file:
        caption = file.read().strip()
    if not caption:
        raise SystemExit("A legenda está vazia; publicação cancelada.")

    image_url = f"{IMAGE_URL_BASE}?v={int(time.time())}"
    session = requests.Session()

    print("Criando contêiner de publicação no Instagram...")
    create = session.post(
        f"{BASE_URL}/{IG_USER_ID}/media",
        data={
            "image_url": image_url,
            "caption": caption,
            "access_token": ACCESS_TOKEN,
        },
        timeout=60,
    )
    fail_for_response(create)
    container_id = create.json().get("id")
    if not container_id:
        raise RuntimeError("A API do Instagram não retornou o ID do contêiner.")
    print("Contêiner criado; aguardando processamento da imagem.")

    ready = False
    for attempt in range(1, 13):
        status_response = session.get(
            f"{BASE_URL}/{container_id}",
            params={"fields": "status_code,status", "access_token": ACCESS_TOKEN},
            timeout=30,
        )
        fail_for_response(status_response)
        status_data = status_response.json()
        status = status_data.get("status_code", "")
        print(f"Status do contêiner ({attempt}/12): {status or 'desconhecido'}")
        if status == "FINISHED":
            ready = True
            break
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(
                f"Contêiner não pode ser publicado: {status}. "
                f"Detalhe: {status_data.get('status', 'sem detalhes')}"
            )
        time.sleep(5)

    if not ready:
        raise RuntimeError("A imagem não ficou pronta para publicação dentro do tempo limite.")

    print("Publicando a imagem no Instagram...")
    publish = session.post(
        f"{BASE_URL}/{IG_USER_ID}/media_publish",
        data={"creation_id": container_id, "access_token": ACCESS_TOKEN},
        timeout=60,
    )
    fail_for_response(publish)
    media_id = publish.json().get("id")
    if not media_id:
        raise RuntimeError("A API não confirmou o ID da publicação.")
    print(f"Publicação concluída. ID da mídia: {media_id}")

if __name__ == "__main__":
    main()
