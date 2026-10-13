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
CLOUDFLARE_IMAGE_MODEL = os.environ.get("WENBOT_IMAGE_MODEL", "@cf/black-forest-labs/flux-2-klein-9b")
CLOUDFLARE_IMAGE_WIDTH = int(os.environ.get("WENBOT_WIDTH", "1024"))
CLOUDFLARE_IMAGE_HEIGHT = int(os.environ.get("WENBOT_HEIGHT", "1024"))
WENBOT_ATTEMPTS = max(1, min(10, int(os.environ.get("WENBOT_ATTEMPTS", "3"))))
WENBOT_SEED = os.environ.get("WENBOT_SEED", "").strip()
RNG = random.Random(int(WENBOT_SEED)) if WENBOT_SEED else random.Random()

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
Base concept: {RNG.choice(ASSUNTOS)}
Camera/composition: {RNG.choice(ANGULOS)}
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
    """Gera com FLUX.2 Klein e tenta FLUX.1 Schnell se houver rate limit/erro transitório."""
    if not CLOUDFLARE_ACCOUNT_ID or not CLOUDFLARE_API_TOKEN:
        raise RuntimeError(
            "Configure CLOUDFLARE_ACCOUNT_ID e CLOUDFLARE_API_TOKEN nos Secrets "
            "do ambiente onde o WenBot é executado."
        )

    if "VISUAL CONCEPT:" in prompt and "\n\nSTYLE:" in prompt:
        inicio, resto = prompt.split("VISUAL CONCEPT:", 1)
        conceito, estilo = resto.split("\n\nSTYLE:", 1)
        prompt_api = f"{inicio}VISUAL CONCEPT:{conceito[:1250]}\n\nSTYLE:{estilo}"
    else:
        prompt_api = prompt[:2000]
    prompt_api = prompt_api[:2048]

    headers = {"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}"}
    modelo_selecionado = CLOUDFLARE_IMAGE_MODEL
    modelo_reserva = (
        "@cf/black-forest-labs/flux-1-schnell"
        if modelo_selecionado != "@cf/black-forest-labs/flux-1-schnell"
        else "@cf/black-forest-labs/flux-2-klein-9b"
    )
    modelos = [
        (modelo_selecionado, "klein" if "klein" in modelo_selecionado else "schnell"),
        (modelo_reserva, "klein" if "klein" in modelo_reserva else "schnell"),
    ]
    ultimo_erro = None

    for modelo, formato in modelos:
        url = (
            "https://api.cloudflare.com/client/v4/accounts/"
            f"{CLOUDFLARE_ACCOUNT_ID}/ai/run/{modelo}"
        )
        for tentativa in range(1, WENBOT_ATTEMPTS + 1):
            try:
                print(
                    f"Gerando imagem com Cloudflare Workers AI ({modelo}, "
                    f"tentativa {tentativa}/{WENBOT_ATTEMPTS})..."
                )
                seed = RNG.randint(1, 999999999)
                if formato == "klein":
                    payload = {
                        "prompt": prompt_api,
                        "width": str(CLOUDFLARE_IMAGE_WIDTH),
                        "height": str(CLOUDFLARE_IMAGE_HEIGHT),
                        "seed": str(seed),
                    }
                    arquivos_form = {chave: (None, valor) for chave, valor in payload.items()}
                    r = requests.post(
                        url, headers=headers, files=arquivos_form, timeout=180
                    )
                else:
                    # FLUX.1 Schnell espera um corpo JSON; data= envia formulário e causa HTTP 400.
                    # O endpoint REST da Cloudflare aceita prompt e seed neste modelo.
                    r = requests.post(
                        url,
                        headers={**headers, "Content-Type": "application/json"},
                        json={
                            "prompt": prompt_api,
                            "seed": seed,
                            "width": CLOUDFLARE_IMAGE_WIDTH,
                            "height": CLOUDFLARE_IMAGE_HEIGHT,
                        },
                        timeout=180,
                    )

                if r.status_code == 429 and tentativa < WENBOT_ATTEMPTS:
                    espera = int(r.headers.get("Retry-After", "30"))
                    espera = max(5, min(espera, 90))
                    print(f"Limite temporário da Cloudflare (429). Aguardando {espera}s...")
                    time.sleep(espera)
                    continue

                if not r.ok:
                    detalhe = (r.text or "").strip().replace("\\n", " ")[:1200]
                    raise requests.HTTPError(
                        f"{r.status_code} {r.reason}; resposta da API: {detalhe}",
                        response=r,
                    )
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
                    raise RuntimeError(f"O modelo {modelo} não retornou o campo de imagem.")

                img = Image.open(io.BytesIO(base64.b64decode(imagem_b64))).convert("RGBA")
                if img.width < 100 or img.height < 100:
                    raise RuntimeError(f"O modelo {modelo} retornou uma imagem inválida.")
                print(f"Imagem gerada com sucesso usando {modelo}.")
                return img

            except Exception as erro:
                ultimo_erro = erro
                status = getattr(getattr(erro, "response", None), "status_code", None)
                print(f"Falha no modelo {modelo}: {erro}")

                # Erros de credencial ou modelo inexistente não melhoram com novas tentativas.
                if status in (400, 401, 403, 404):
                    break
                if tentativa == 1 and status != 429:
                    time.sleep(10)
                    continue
                # Após duas tentativas, avança para o modelo alternativo.
                break

    raise RuntimeError(
        "Não foi possível gerar a imagem com os modelos alternativos da Cloudflare. "
        "O limite/cota da conta pode ter sido atingido. Último erro: "
        f"{ultimo_erro}"
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
