import base64
import io
import os
import random
import time

import requests
from PIL import Image, ImageDraw, ImageFont
from google import genai

USUARIO_GITHUB = "gjngngvb-byte"
NOME_REPO = "WenBot_Final"
NOME_DO_ARQUIVO_FONTE = "Quentin.otf"
TAMANHO_DA_ASSINATURA = 60
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GEMINI_MODEL = "gemini-3.8-flash"

# Cloudflare Workers AI: use apenas o plano Free para evitar cobranças.
CLOUDFLARE_ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
CLOUDFLARE_API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN")
CLOUDFLARE_IMAGE_MODEL = "@cf/black-forest-labs/flux-2-klein-9b"
CLOUDFLARE_IMAGE_WIDTH = 1024
CLOUDFLARE_IMAGE_HEIGHT = 1024

if not GOOGLE_API_KEY:
    raise RuntimeError("GOOGLE_API_KEY não configurada.")

client = genai.Client(api_key=GOOGLE_API_KEY)

def gerar_conteudo_com_retentativas(**kwargs):
    """Repete falhas transitórias, mas não insiste quando a cota foi esgotada."""
    ultimo_erro = None
    for tentativa in range(1, 4):
        try:
            return client.models.generate_content(**kwargs)
        except Exception as erro:
            ultimo_erro = erro
            mensagem = str(erro).upper()

            # Cota diária esgotada não será resolvida por novas tentativas imediatas.
            if "RESOURCE_EXHAUSTED" in mensagem or "QUOTA EXCEEDED" in mensagem:
                raise

            temporario = any(
                termo in mensagem
                for termo in ("503", "UNAVAILABLE", "429", "500", "INTERNAL", "SERVER DISCONNECTED")
            )
            if not temporario or tentativa == 3:
                raise

            espera = tentativa * 15
            print(
                f"Gemini temporariamente indisponível "
                f"(tentativa {tentativa}/3). Nova tentativa em {espera}s..."
            )
            time.sleep(espera)
    raise ultimo_erro

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
Create ONE original concept for a clean, digital-looking 2D illustration inspired by the user's established spider-reference art style. Do not recreate the spider or any reference image.
Base concept: {random.choice(ASSUNTOS)}
Camera/composition: {random.choice(ANGULOS)}
STYLE: crisp, deliberate black vector-like outlines on a pure white background, using simple geometric shapes and clean curves. The design should feel graphic, minimal, clever, and imaginative, with a strong readable silhouette and an unusual viewpoint. Keep the subject flat and clearly illustrated, not rendered in 3D.
ABSOLUTELY NO color, gray, shading, shadows, gradients, texture, hatching, sketchy strokes, paint effects, lettering, text, logos, watermarks, or signatures. The bot will add the only signature, "Wen", separately after generation.
Return ONLY the visual description in English, maximum 180 words.
""".strip()
    try:
        r = gerar_conteudo_com_retentativas(model=GEMINI_MODEL, contents=prompt)
        texto = (r.text or "").strip()
        if texto:
            return texto[:1800]
        print("Gemini retornou uma ideia vazia; usando conceito local.")
    except Exception as erro:
        print(
            f"Gemini indisponível para criar o conceito "
            f"({type(erro).__name__}). Usando conceito local para continuar."
        )

    # Plano B sem API: a geração da arte continua mesmo quando a cota do Gemini acaba.
    assunto = random.choice(ASSUNTOS)
    angulo = random.choice(ANGULOS)
    return (
        f"Create an original imaginative subject based on: {assunto}. "
        f"Composition and viewpoint: {angulo}. "
        "Use a clean, flat 2D design made from simple geometric shapes, "
        "crisp black outlines, pure white background, and a strong readable silhouette. "
        "Keep it beautiful, unusual, and understandable. No color, gray, fill, "
        "shading, shadows, gradients, lighting, texture, hatching, text, or 3D effects."
    )

def baixar_imagem(prompt):
    """Gera a imagem com Cloudflare Workers AI, sem alterar o fluxo do Gemini/Instagram."""
    if not CLOUDFLARE_ACCOUNT_ID or not CLOUDFLARE_API_TOKEN:
        raise RuntimeError(
            "Configure CLOUDFLARE_ACCOUNT_ID e CLOUDFLARE_API_TOKEN nos Secrets "
            "do ambiente onde o WenBot é executado."
        )

    # Mantém o conceito e as instruções de estilo no prompt do FLUX.2 Klein 9B.
    if "VISUAL CONCEPT:" in prompt and "\n\nSTYLE:" in prompt:
        inicio, resto = prompt.split("VISUAL CONCEPT:", 1)
        conceito, estilo = resto.split("\n\nSTYLE:", 1)
        prompt_api = f"{inicio}VISUAL CONCEPT:{conceito[:1250]}\n\nSTYLE:{estilo}"
    else:
        prompt_api = prompt[:2000]
    prompt_api = prompt_api[:2048]
    url = (
        "https://api.cloudflare.com/client/v4/accounts/"
        f"{CLOUDFLARE_ACCOUNT_ID}/ai/run/{CLOUDFLARE_IMAGE_MODEL}"
    )
    # FLUX.2 Klein 9B exige multipart/form-data; steps é fixo em 4 no serviço.
    payload = {
        "prompt": prompt_api,
        "width": str(CLOUDFLARE_IMAGE_WIDTH),
        "height": str(CLOUDFLARE_IMAGE_HEIGHT),
        "seed": str(random.randint(1, 999999999)),
    }
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
    }

    ultimo_erro = None
    for tentativa in range(1, 4):
        try:
            print(
                f"Gerando imagem com Cloudflare Workers AI "
                f"(tentativa {tentativa}/3)..."
            )
            arquivos_form = {
                chave: (None, valor)
                for chave, valor in payload.items()
            }
            r = requests.post(
                url,
                headers=headers,
                files=arquivos_form,
                timeout=180,
            )
            r.raise_for_status()
            data = r.json()

            if data.get("success") is False:
                errors = data.get("errors") or []
                mensagem = "; ".join(
                    str(item.get("message", item)) for item in errors
                ) or "Cloudflare retornou success=false."
                raise RuntimeError(mensagem)

            resultado = data.get("result") or {}
            imagem_b64 = resultado.get("image")
            if not imagem_b64:
                raise RuntimeError("Cloudflare não retornou o campo de imagem.")

            img = Image.open(io.BytesIO(base64.b64decode(imagem_b64))).convert("RGBA")
            if img.width < 100 or img.height < 100:
                raise RuntimeError("Cloudflare retornou uma imagem inválida.")
            return img
        except Exception as e:
            ultimo_erro = e
            print(f"Falha no Cloudflare Workers AI: {e}")
            # Erros de autenticação/configuração/limite não melhoram repetindo
            # a mesma chamada, então interrompe para evitar tentativas inúteis.
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status in (400, 401, 403, 404, 429):
                break

    raise RuntimeError(
        f"Falha ao gerar imagem com Cloudflare Workers AI: {ultimo_erro}"
    )

def salvar_arte(img):
    """Aplica fundo branco e uma assinatura consistente, renderizada em alta resolução."""
    fundo = Image.new("RGBA", img.size, "WHITE")
    fundo.alpha_composite(img.convert("RGBA"))

    largura, altura = fundo.size
    escala = 2
    tamanho = max(28, min(TAMANHO_DA_ASSINATURA, round(largura * 0.058)))
    margem = max(18, round(largura * 0.035))
    camada = Image.new("RGBA", (largura * escala, altura * escala), (255, 255, 255, 0))
    desenho = ImageDraw.Draw(camada)

    try:
        fonte = ImageFont.truetype(NOME_DO_ARQUIVO_FONTE, tamanho * escala)
    except (OSError, ValueError):
        print(f"Aviso: fonte {NOME_DO_ARQUIVO_FONTE} indisponível; usando fonte padrão.")
        fonte = ImageFont.load_default()

    texto = "Wen"
    caixa = desenho.textbbox((0, 0), texto, font=fonte)
    texto_largura = caixa[2] - caixa[0]
    texto_altura = caixa[3] - caixa[1]
    x = largura * escala - texto_largura - margem * escala - caixa[0]
    y = altura * escala - texto_altura - margem * escala - caixa[1]
    desenho.text((x, y), texto, fill=(0, 0, 0, 255), font=fonte)

    camada = camada.resize((largura, altura), Image.Resampling.LANCZOS)
    fundo = Image.alpha_composite(fundo, camada)
    fundo.convert("RGB").save("wen_art.jpg", "JPEG", quality=95, optimize=True)

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

    try:
        r = gerar_conteudo_com_retentativas(model=GEMINI_MODEL, contents=[prompt, imagem])
        legenda = (r.text or "").strip()
        if legenda and "#wen" in legenda.lower() and "#art" in legenda.lower():
            return legenda
        print("Gemini retornou uma legenda vazia ou sem as hashtags obrigatórias.")
    except Exception as e:
        print(f"Gemini não conseguiu criar a legenda: {type(e).__name__}: {e}")

    # A falta de cota para legendas não deve impedir a publicação da arte.
    # Esta legenda neutra evita afirmar detalhes visuais que não foram verificados.
    print("Usando legenda de reserva em português para não interromper o fluxo.")
    return (
        "Às vezes, basta mudar o ponto de vista para o impossível ganhar forma.\n\n"
        "#wen #art #arte #desenho #surrealismo"
    )

def criar_arte():
    ideia = gerar_ideia()
    print(f"Conceito: {ideia}")
    prompt = f"""
Create a polished illustration in the same clean graphic style as the spider reference the user shared earlier. Use the reference ONLY for its visual style, never recreate its subject or composition.

VISUAL CONCEPT:
{ideia}

MANDATORY STYLE:
- Pure white background (#FFFFFF).
- Pure black linework only (#000000), with no other colors and no gray.
- Clean, digital-looking 2D illustration, like precise black ink/vector line art.
- Build forms from simple geometric shapes and clean, intentional curves.
- Strong, clear silhouette; minimal but distinctive details; visually attractive, imaginative, and easy to read.
- Use a surprising, unconventional camera angle while keeping the artwork flat and graphic.
- Use crisp, consistent outlines. Avoid messy, rough, sketchy or painterly marks.
- Keep the bottom-right corner relatively uncluttered for the signature that the bot adds afterward.
- Invent a new subject and composition each time. The reference is only a style guide.

STRICTLY FORBIDDEN:
Any color, colored accents, gray or grayscale, gradients, shading, shadows, highlights, lighting effects, 3D rendering, simulated volume, photorealism, hatching, cross-hatching, scribbles, sketchy strokes, paint texture, watercolor, pencil texture, paper texture, halftones, fills, borders, frames, beige/off-white backgrounds, text, letters, numbers, logos, brand names, labels, watermarks, AI/provider marks, or signatures.

Do not generate any text, including "Wen". The bot adds the only signature, the exact word "Wen", afterward as a separate overlay. The final result must look like a crisp, clean black geometric line illustration on pure white.
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
