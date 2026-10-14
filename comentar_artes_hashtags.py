import json
import os
import random
import re
import sys
import time
import unicodedata
from pathlib import Path

from instagrapi import Client
from google import genai

HISTORY_PATH = Path("wen_art_hashtag_comments.json")
# Limite conservador por execução. O workflow agenda até cinco execuções por dia.
MAX_COMMENTS_PER_RUN = 3
MEDIA_PER_HASHTAG = 8

# 30 hashtags prioritárias para encontrar desenhos e ilustrações.
# Foco em arte autoral, desenho, sketch e line art, alinhado ao perfil Wen.
HASHTAGS = [
    "desenho", "arte", "ilustracao", "desenhodigital", "desenhosautorais",
    "desenhosoriginais", "desenhopretoebranco", "desenhando", "rabisco",
    "artedigital", "artesbrasileiras", "desenhoartistico", "lineart",
    "blackandwhiteart", "drawing", "drawings", "illustration", "artwork",
    "sketch", "sketchbook", "pencildrawing", "inkdrawing", "inkillustration",
    "digitalillustration", "digitaldrawing", "characterdesign", "conceptart",
    "originalartwork", "handdrawnart", "creativeillustration",
]

# Frases curtas, coloquiais e adequadas a vários estilos de arte.
PT_COMMENTS = [
    "nuusa, q bonito", "ficou muito showww", "inveja de quem desenha assim 😮‍💨",
    "mds, ficou lindo", "caraca, q arte bonita", "isso ficou brabo demais",
    "o talento dessa pessoa 😭", "ficou chique dms", "que capricho, sério",
    "tá muito lindo isso", "aí simmm 🎉", "ficou bom demais", "que coisa linda, véi",
    "o tanto que eu gostei disso", "isso tá show de bola", "perfeição viu",
    "nu, mandou muito", "ficou incrível dms", "essa ficou top demais",
    "que desenho gostoso de olhar", "talento puro, slk", "ficou absurdo de bom",
    "amei real oficial", "isso merece muito mais atenção", "bonito pra caramba",
    "ficou massa demais", "que trabalho lindo 🫶", "brabooo demais",
    "eu queria desenhar assim 😭", "simplesmente lindo", "olha esse capricho!",
    "ficou show demais 🎉", "meu deus, que bonito", "a vibe dessa arte tá boa demais",
    "mandou bem demais", "isso ficou uma gracinha", "arte linda da conta",
    "tá de parabéns demais", "ficou fino viu", "que desenho maravilhoso",
    "aí você esculachou", "ficou bonito demais, sério", "essa ficou pancada",
    "que talento absurdo", "amei essa aqui", "tá muito daora", "ficou bom viu!",
    "nossa senhora, que arte", "isso tá lindo demaisss", "obra de milhões 😮‍💨",
    "o artista entregou tudo", "essa ficou braba", "simplesmente showww",
    "que coisa mais linda 🎉", "ficou delicinha de olhar", "arrasou nessa",
    "isso ficou muito irado", "bonito demais da conta", "eu curti muito essa",
    "ficou surreal de bom", "a qualidade tá absurda", "perfeita essa arte",
]

EN_COMMENTS = [
    "this looks so good!", "such a cool piece 🎉", "love the vibe of this",
    "this is seriously beautiful", "so much talent here", "this turned out amazing",
    "the details are so good", "this is awesomeee", "such a lovely artwork",
    "this goes hard 😮‍💨", "really nice work!", "this looks incredible",
    "the style is so cool", "absolutely love this", "what a beautiful piece",
    "this is so satisfying to look at", "great work on this!", "so freaking cool",
    "you nailed this one", "this deserves more love", "such a clean drawing",
    "this is beautiful ✨", "love how this turned out", "seriously impressive",
    "this is a whole vibe", "so cool, wow", "amazing work 🎉",
    "the talent is unreal", "this looks fantastic", "I really like this one",
]

ES_COMMENTS = [
    "¡qué bonito quedó!", "me encanta este estilo ✨", "te quedó increíble",
    "qué trabajazo, de verdad", "está precioso", "muchísimo talento aquí",
    "me gusta muchísimo esta pieza", "qué buena vibra tiene", "te luciste con este",
    "está genial 🎉", "qué arte tan bonito", "me encanta cómo quedó",
    "esto merece más amor", "qué nivel de detalle", "una belleza de dibujo",
]

FR_COMMENTS = [
    "c'est vraiment magnifique !", "j'adore ce style ✨", "super beau travail",
    "beaucoup de talent ici", "le résultat est incroyable", "c'est trop joli",
    "j'aime beaucoup cette création", "quelle belle illustration", "très réussi !",
    "c'est superbe 🎉", "les détails sont magnifiques", "j'adore le rendu",
    "ça mérite plus d'amour", "un travail vraiment impressionnant", "trop stylé !",
]

PT_MARKERS = {
    "desenho", "desenhos", "arte", "artes", "ilustração", "ilustracao",
    "feito", "feita", "meu", "minha", "estudo", "rabisco", "pintura",
    "lápis", "lapis", "brasil", "brasileiro", "brasileira", "desenhando",
    "personagem", "fanartbrasil", "artedigital",
}
EN_MARKERS = {
    "drawing", "artwork", "sketch", "illustration", "myart", "artist",
    "digitalart", "painting", "made", "character", "fanart", "wip", "the", "this", "my",
}
ES_MARKERS = {
    "dibujo", "dibujos", "ilustracion", "ilustración", "arte", "artista", "boceto",
    "pintura", "lapiz", "lápiz", "hecho", "hecha", "personaje", "miarte", "creativo",
    "hermoso", "bonito", "precioso", "gracias", "hola", "espanol", "español",
}
FR_MARKERS = {
    "dessin", "dessins", "illustration", "artiste", "croquis", "peinture", "crayon",
    "personnage", "monart", "magnifique", "beau", "belle", "merci", "bonjour",
    "création", "creation", "français", "francais", "oeuvre", "œuvre", "fait", "faite",
}


def field(obj, name, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def load_history():
    try:
        data = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.setdefault("commented_media_ids", [])
            data.setdefault("used_comments", [])
            data.setdefault("comment_log", [])
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {"commented_media_ids": [], "used_comments": [], "comment_log": []}


def normalize(text):
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text).strip()


def detect_language(media):
    caption = str(field(media, "caption_text", "") or "")
    tags = " ".join(re.findall(r"#([\w]+)", caption.lower()))
    content = normalize(caption + " " + tags)
    scores = {
        "pt": sum(1 for word in PT_MARKERS if normalize(word) in content),
        "en": sum(1 for word in EN_MARKERS if normalize(word) in content),
        "es": sum(1 for word in ES_MARKERS if normalize(word) in content),
        "fr": sum(1 for word in FR_MARKERS if normalize(word) in content),
    }
    # Em caso de dúvida, prioriza português brasileiro; se houver texto sem sinais claros, usa inglês.
    if max(scores.values()) == 0:
        return "pt" if not caption else "en"
    return max(scores, key=scores.get)


def choose_comment(language_code, used_comments, caption=""):
    pools = {"pt": PT_COMMENTS, "en": EN_COMMENTS, "es": ES_COMMENTS, "fr": FR_COMMENTS}
    language_names = {
        "pt": "português brasileiro bem informal, com gírias naturais",
        "en": "casual, natural English",
        "es": "español natural y coloquial",
        "fr": "français naturel et courant",
    }
    pool = pools.get(language_code, EN_COMMENTS)
    used_normalized = {normalize(item) for item in used_comments}
    api_key = os.environ.get("GOOGLE_API_KEY", "").strip()

    # A IA cria variações novas, usando o histórico para evitar frases repetidas.
    if api_key:
        try:
            client = genai.Client(api_key=api_key)
            language = language_names.get(language_code, "casual, natural English")
            recent = used_comments[-80:]
            for _ in range(3):
                prompt = (
                    "Escreva um comentário elogioso muito curto para uma publicação de arte no Instagram. "
                    f"Idioma e estilo: {language}. "
                    "Pode ser uma reação espontânea, uma frase ou apenas emojis. "
                    "Seja positivo e natural; não invente detalhes específicos sobre a imagem. "
                    "Não use hashtags, perguntas, links nem mais de 100 caracteres. "
                    "Crie uma formulação nova, não parecida com os exemplos já usados. "
                    f"Legenda/hashtags da publicação: {caption[:500]}\n"
                    f"Comentários já usados, que devem ser evitados: {recent}\n"
                    "Retorne somente o comentário."
                )
                result = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=prompt,
                )
                answer = (result.text or "").strip().strip('"').strip("'")
                answer = re.sub(r"^@\w+\s*", "", answer).strip()
                if answer and len(answer) <= 100 and normalize(answer) not in used_normalized:
                    return answer
        except Exception as exc:
            print(f"IA indisponível para criar elogio: {type(exc).__name__}: {exc}")

    candidates = [item for item in pool if normalize(item) not in used_normalized]
    if not candidates:
        print("Sem elogios inéditos disponíveis no modo local; publicação ignorada.")
        return None
    return random.choice(candidates)


def main():
    session_json = os.environ.get("INSTAGRAM_SESSION", "").strip()
    if not session_json:
        raise RuntimeError("Secret INSTAGRAM_SESSION não configurado.")
    settings = json.loads(session_json)

    client = Client()
    client.set_settings(settings)
    client.get_timeline_feed()
    own_user_id = str(client.user_id)

    history = load_history()
    commented_ids = {str(item) for item in history["commented_media_ids"]}
    used_comments = list(history["used_comments"])
    used_normalized = {normalize(item) for item in used_comments}

    found = {}
    search_successes = 0
    search_errors = 0
    total_hashtags = len(HASHTAGS)
    for hashtag_index, hashtag in enumerate(HASHTAGS, start=1):
        print(f"Consultando hashtag {hashtag_index}/{total_hashtags}: #{hashtag}", flush=True)
        try:
            medias = client.hashtag_medias_recent(hashtag, amount=MEDIA_PER_HASHTAG)
            search_successes += 1
            for media in medias:
                media_id = str(field(media, "pk", "") or "")
                media_user = field(media, "user", {}) or {}
                media_user_id = str(field(media, "user_id", "") or field(media_user, "pk", ""))
                if not media_id or media_id in commented_ids or media_user_id == own_user_id:
                    continue
                # Apenas publicações de outras contas encontradas pelas hashtags.
                found.setdefault(media_id, media)
        except Exception as exc:
            search_errors += 1
            print(f"Hashtag #{hashtag} indisponível: {type(exc).__name__}: {exc}")
            continue

    candidates = list(found.values())
    random.shuffle(candidates)
    print(f"Encontradas {len(candidates)} publicações ainda não comentadas.")

    sent = 0
    post_failures = 0
    for media in candidates:
        if sent >= MAX_COMMENTS_PER_RUN:
            print(f"Limite de {MAX_COMMENTS_PER_RUN} comentários nesta execução atingido.")
            break

        media_id = str(field(media, "pk", "") or "")
        language_code = detect_language(media)
        comment = choose_comment(language_code, used_comments, str(field(media, "caption_text", "") or ""))
        if not comment or normalize(comment) in used_normalized:
            continue

        try:
            client.media_comment(media_id, comment)
            commented_ids.add(media_id)
            used_comments.append(comment)
            used_normalized.add(normalize(comment))
            media_user = field(media, "user", {}) or {}
            history.setdefault("comment_log", []).append({
                "media_id": media_id,
                "username": str(field(media_user, "username", "") or ""),
                "caption": str(field(media, "caption_text", "") or "")[:300],
                "comment": comment,
                "commented_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })
            history["comment_log"] = history["comment_log"][-300:]
            history["commented_media_ids"] = sorted(commented_ids)
            history["used_comments"] = used_comments
            HISTORY_PATH.write_text(
                json.dumps(history, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            sent += 1
            print(f"Comentário enviado à publicação {media_id}: {comment}")
            time.sleep(2)
        except Exception as exc:
            post_failures += 1
            print(f"Falha ao comentar na publicação {media_id}: {type(exc).__name__}: {exc}")
            # Não registra como concluído se o envio falhou.

    HISTORY_PATH.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Concluído: {sent} comentário(s) em artes encontradas por hashtag.")
    print(f"Diagnóstico: {search_successes} hashtag(s) consultada(s) com sucesso; {search_errors} erro(s) de busca; {post_failures} falha(s) ao comentar.")
    if sent == 0 and (search_successes == 0 or post_failures > 0):
        raise RuntimeError("Nenhum comentário foi enviado e a busca ou o envio apresentou falhas. Consulte as mensagens acima.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Falha na busca/comentários por hashtag: {type(exc).__name__}: {exc}")
        # Esta função é complementar e não deve desfazer a publicação da arte própria.
        sys.exit(1)
