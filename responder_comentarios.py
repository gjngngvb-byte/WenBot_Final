import json
import os
import re
import sys
import time
from pathlib import Path

import requests
from google import genai
from instagrapi import Client

HISTORY_PATH = Path("wen_comment_replies.json")
MAX_REPLIES_PER_RUN = 20
GEMINI_MODEL = "gemini-3.8-flash"


def value(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def load_history():
    try:
        data = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.setdefault("replied_comment_ids", [])
            data.setdefault("replies", [])
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {"replied_comment_ids": [], "replies": []}


def generate_reply(comment_text, caption, username, previous_replies):
    prompt = f"""
Você responde comentários do perfil artístico Wen no Instagram.
Escreva UMA resposta curta, humana, simpática e específica ao comentário recebido.
Primeiro identifique o idioma do comentário recebido e responda no MESMO idioma, mantendo a variante natural desse idioma. Use português brasileiro somente se a pessoa comentou em português; se comentou em inglês, responda em inglês; faça o mesmo com espanhol, francês e outros idiomas que conseguir identificar.
Considere a legenda da publicação e o sentido do comentário para responder de forma coerente, sem responder apenas com um agradecimento genérico quando a pessoa fez uma pergunta ou comentou algo específico.
Não seja robótico, não use frases prontas, não repita respostas anteriores.
Não invente fatos sobre a imagem ou sobre o autor. Não prometa nada, não peça dados pessoais.
Não inclua hashtags, links ou mais de um emoji. Responda diretamente ao que a pessoa disse.
Se for apenas um emoji, agradeça de forma natural e breve.
Legenda da publicação: {caption[:1200]}
Nome público de quem comentou: {username[:80]}
Comentário recebido: {comment_text[:1500]}
Respostas recentes usadas pelo perfil, evite repeti-las: {previous_replies[-12:] or "nenhuma"}
Retorne somente a resposta, com no máximo 240 caracteres.
""".strip()

    google_key = os.environ.get("GOOGLE_API_KEY", "").strip()
    if google_key:
        try:
            client = genai.Client(api_key=google_key)
            result = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
            answer = (result.text or "").strip().strip('"').strip("'")
            if answer:
                return answer[:240]
            print("Gemini não retornou texto para a resposta.")
        except Exception as exc:
            print(f"Gemini indisponível para responder comentário: {type(exc).__name__}: {exc}")

    account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    if account_id and token:
        url = (
            "https://api.cloudflare.com/client/v4/accounts/"
            f"{account_id}/ai/run/@cf/meta/llama-3.1-8b-instruct"
        )
        response = requests.post(
            url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"messages": [
                {"role": "system", "content": "Você escreve respostas breves, naturais e personalizadas para comentários no Instagram."},
                {"role": "user", "content": prompt},
            ]},
            timeout=60,
        )
        response.raise_for_status()
        answer = ((response.json().get("result") or {}).get("response") or "").strip().strip('"').strip("'")
        if answer:
            return answer[:240]

    raise RuntimeError("Nenhuma IA conseguiu criar uma resposta; comentário ficará pendente.")


def main():
    session_json = os.environ.get("INSTAGRAM_SESSION", "").strip()
    if not session_json:
        raise RuntimeError("Secret INSTAGRAM_SESSION não configurado.")
    try:
        settings = json.loads(session_json)
    except json.JSONDecodeError as exc:
        raise RuntimeError("INSTAGRAM_SESSION não contém JSON válido.") from exc

    # Em publicação normal, exclui a arte recém-publicada. No modo manual de respostas,
    # NEW_MEDIA_PK fica vazio e o bot revisa as publicações existentes.
    new_media_pk = os.environ.get("NEW_MEDIA_PK", "").strip()

    client = Client()
    client.delay_range = [4, 9]
    client.set_settings(settings)
    client.get_timeline_feed()

    own_user_id = str(client.user_id)
    history = load_history()
    replied_ids = {str(item) for item in history["replied_comment_ids"]}
    previous_replies = [
        item.get("reply", "") for item in history["replies"] if isinstance(item, dict)
    ]

    medias = client.user_medias(client.user_id, amount=100)
    previous_medias = [media for media in medias if str(value(media, "pk", "")) != new_media_pk] if new_media_pk else medias

    # Guarda links reais para que o painel abra a publicação e o comentário correspondente.
    media_codes = {
        str(value(media, "pk", "")): str(value(media, "code", "") or "")
        for media in medias
    }
    history_changed = False
    for record in history["replies"]:
        if not isinstance(record, dict):
            continue
        code = media_codes.get(str(record.get("media_id", "")), "")
        if code:
            media_url = f"https://www.instagram.com/p/{code}/"
            comment_url = f"{media_url}c/{record.get('comment_id', '')}/" if record.get("comment_id") else media_url
            if record.get("media_url") != media_url or record.get("comment_url") != comment_url or record.get("reply_url") != comment_url:
                record["media_url"] = media_url
                record["comment_url"] = comment_url
                record["reply_url"] = comment_url
                history_changed = True
    if history_changed:
        HISTORY_PATH.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Publicação nova: {new_media_pk}. Verificando {len(previous_medias)} publicações anteriores.")

    sent = 0
    for media in previous_medias:
        if sent >= MAX_REPLIES_PER_RUN:
            print(f"Limite de {MAX_REPLIES_PER_RUN} respostas nesta execução atingido; o restante fica para a próxima.")
            break

        media_pk = str(value(media, "pk", ""))
        caption = value(media, "caption_text", "") or ""
        try:
            comments = client.media_comments(media_pk, amount=100)
        except Exception as exc:
            print(f"Não foi possível ler comentários da publicação {media_pk}: {type(exc).__name__}: {exc}")
            continue

        for comment in comments:
            if sent >= MAX_REPLIES_PER_RUN:
                break
            comment_pk = str(value(comment, "pk", ""))
            if not comment_pk or comment_pk in replied_ids:
                continue

            text = (value(comment, "text", "") or "").strip()
            user = value(comment, "user", {}) or {}
            commenter_id = str(value(comment, "user_id", "") or value(user, "pk", ""))
            username = str(value(user, "username", "") or "pessoa")
            parent_id = value(comment, "parent_comment_id", None)
            child_count = int(value(comment, "child_comment_count", 0) or 0)

            # Nunca responde a si próprio nem cria conversas dentro de respostas existentes.
            if commenter_id and commenter_id == own_user_id:
                continue
            if parent_id:
                continue
            # Se já existe uma resposta pública neste comentário, deixa-o em paz.
            if child_count > 0:
                replied_ids.add(comment_pk)
                history["replied_comment_ids"] = sorted(replied_ids)
                continue
            if not text:
                continue

            try:
                answer = generate_reply(text, caption, username, previous_replies)
                client.media_comment(media_pk, answer, replied_to_comment_id=comment.pk)
                replied_ids.add(comment_pk)
                previous_replies.append(answer)
                history["replied_comment_ids"] = sorted(replied_ids)
                media_code = str(value(media, "code", "") or "")
                media_url = f"https://www.instagram.com/p/{media_code}/" if media_code else ""
                comment_url = f"{media_url}c/{comment_pk}/" if media_url else ""
                history["replies"].append({
                    "comment_id": comment_pk,
                    "media_id": media_pk,
                    "username": username,
                    "comment": text[:300],
                    "reply": answer,
                    "media_url": media_url,
                    "comment_url": comment_url,
                    "reply_url": comment_url,
                    "replied_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                })
                HISTORY_PATH.write_text(
                    json.dumps(history, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                sent += 1
                print(f"Respondido @{username} na publicação {media_pk}.")
                time.sleep(3)
            except Exception as exc:
                print(f"Falha ao responder comentário {comment_pk}: {type(exc).__name__}: {exc}")
                # Não marca como respondido: será tentado novamente numa publicação futura.
                continue

    HISTORY_PATH.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Concluído: {sent} comentário(s) respondido(s).")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Falha no processamento de comentários: {type(exc).__name__}: {exc}")
        # A publicação já ocorreu; não transformar uma falha de comentários em falha de publicação.
        sys.exit(0)
