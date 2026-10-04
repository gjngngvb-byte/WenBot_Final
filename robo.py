import io
import os
import random
import urllib.parse

import requests
from PIL import Image, ImageDraw, ImageFont
from google import genai

USUARIO_GITHUB = "gjngngvb-byte"
NOME_REPO = "WenBot_Final"
NOME_DO_ARQUIVO_FONTE = "Quentin.otf"
TAMANHO_DA_ASSINATURA = 60
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GEMINI_MODEL = "gemini-3.8-flash"

if not GOOGLE_API_KEY:
    raise RuntimeError("GOOGLE_API_KEY não configurada.")

client = genai.Client(api_key=GOOGLE_API_KEY)

ASSUNTOS = [
    "an impossible animal combining two unrelated creatures",
    "an everyday object behaving like a living creature",
    "a strange machine with an impossible purpose",
    "a surreal building that could not exist in the real world",
    "a mysterious character made from an unexpected material",
    "a hybrid between nature and advanced technology",
    "a futuristic object from an unknown civilization",
    "an impossible underwater scene",
    "an ordinary object containing an entire miniature world",
    "a gigantic object seen from the perspective of something tiny",
    "a tiny world hidden inside a common object",
    "an impossible vehicle crossing an ordinary street",
    "a bizarre botanical organism with mechanical details",
    "a surreal creature appearing in a completely ordinary place",
    "a dreamlike city with one physically impossible element",
]

ANGULOS = [
    "extreme bird's-eye view", "extreme worm's-eye view",
    "dramatic low-angle perspective", "dramatic high-angle perspective",
    "steep diagonal perspective", "macro close-up with exaggerated depth",
    "three-quarter view with strong foreshortening", "top-down perspective",
    "side perspective with unusual depth",
    "extreme perspective from an impossible position",
]

def gerar_ideia():
    prompt = f"""
Create ONE unique visual concept for a surreal black-ink drawing.
Base concept: {random.choice(ASSUNTOS)}
Camera/composition: {random.choice(ANGULOS)}
Make it visually clear, strange and unexpected. Avoid generic fantasy clichés.
Return ONLY the visual description in English, maximum 220 words.
""".strip()
    r = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    texto = (r.text or "").strip()
    if not texto:
        raise RuntimeError("Gemini não retornou uma ideia.")
    return texto[:1800]

def baixar_imagem(prompt):
    ultimo_erro = None
    for tentativa in range(1, 4):
        try:
            seed = random.randint(1, 999999999)
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt, safe='')}?width=1024&height=1024&seed={seed}&nologo=true&model=flux"
            print(f"Gerando imagem (tentativa {tentativa}/3)...")
            r = requests.get(url, timeout=180)
            r.raise_for_status()
            if "image" not in r.headers.get("Content-Type", "").lower():
                raise RuntimeError("Servidor não retornou uma imagem.")
            img = Image.open(io.BytesIO(r.content)).convert("RGBA")
            if img.width < 100 or img.height < 100:
                raise RuntimeError("Imagem inválida.")
            return img
        except Exception as e:
            ultimo_erro = e
            print(f"Falha: {e}")
    raise RuntimeError(f"Falha após 3 tentativas: {ultimo_erro}")

def salvar_arte(img):
    fundo = Image.new("RGBA", img.size, "WHITE")
    fundo.alpha_composite(img)
    d = ImageDraw.Draw(fundo)
    try:
        fonte = ImageFont.truetype(NOME_DO_ARQUIVO_FONTE, TAMANHO_DA_ASSINATURA)
    except Exception:
        fonte = ImageFont.load_default()
    texto = "Wen"
    box = d.textbbox((0, 0), texto, font=fonte)
    d.text((fundo.width-(box[2]-box[0])-35, fundo.height-(box[3]-box[1])-35), texto, fill="black", font=fonte)
    fundo.convert("RGB").save("wen_art.jpg", "JPEG", quality=95)

def analisar_imagem_e_criar_legenda():
    print("Analisando a imagem REAL com Gemini...")
    imagem = Image.open("wen_art.jpg").convert("RGB")
    prompt = """
Analyze THIS ACTUAL IMAGE, not just the original concept.
Write a ready-to-post Instagram caption in Brazilian Portuguese.
Describe only what is visible. Consider subject, action, unusual perspective,
composition, atmosphere and surreal details. Be human, intriguing and slightly
poetic. Maximum 4 short lines before hashtags. Never invent details. Never mention
AI, Gemini, Pollinations, prompts, automation or image generation.
Finish with exactly 5 relevant hashtags, always including #wen and #art.
Put hashtags on the last line. Return ONLY the final caption.
""".strip()
    for tentativa in range(1, 4):
        try:
            r = client.models.generate_content(model=GEMINI_MODEL, contents=[prompt, imagem])
            legenda = (r.text or "").strip()
            if legenda and "#wen" in legenda.lower() and "#art" in legenda.lower():
                return legenda
        except Exception as e:
            print(f"Falha na análise {tentativa}/3: {e}")
    raise RuntimeError("Não foi possível criar a legenda.")

def criar_arte():
    ideia = gerar_ideia()
    print(f"Conceito: {ideia}")
    prompt = f"""
Hand-drawn black ink pen illustration on clean white paper.

VISUAL CONCEPT:
{ideia}

STYLE:
black ink only, expressive hand-drawn pen strokes, fine linework,
varied line weight, clean white negative space, surreal artistic illustration,
unusual unconventional camera angle, dynamic perspective, strong composition,
clear silhouette, detailed pen hatching, monochrome.

STRICTLY AVOID:
color, photorealism, 3D render, painting, watercolor, colored pencil,
gray digital gradients, text, logos, border, frame.
""".strip()
    img = baixar_imagem(prompt)
    salvar_arte(img)
    legenda = analisar_imagem_e_criar_legenda()
    open("wen_art.txt", "w", encoding="utf-8").write(legenda)
    open("wen_art_idea.txt", "w", encoding="utf-8").write(ideia)
    print(legenda)
    return legenda

if __name__ == "__main__":
    criar_arte()
