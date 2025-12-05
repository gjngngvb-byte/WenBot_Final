import os
import requests
import urllib.parse
from PIL import Image, ImageDraw, ImageFont
import google.generativeai as genai

# --- CONFIGURAÇÕES (PREENCHA AQUI) ---
# Exemplo: se seu site é joao.github.io/bot-wen
USUARIO_GITHUB = "gjngngvb-byte"  # Coloque seu usuário do GitHub
NOME_REPO = "WenBot_Final"      # Coloque o nome da pasta/repositório

# Segredos
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
MAKE_WEBHOOK_URL = os.environ.get("MAKE_WEBHOOK_URL")

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

def criar_arte():
    print("1. Gerando arte...")
    try:
        model = genai.GenerativeModel("gemini-2.5-flash-preview-09-2025")
        tema = model.generate_content("Ideia visual surreal curta em Inglês.").text.strip()
    except: tema = "Surreal object"
    
    # Gera imagem
    prompt = f"Hand-drawn black ballpoint pen sketch. Subject: {tema}. intricate details."
    safe_prompt = urllib.parse.quote(prompt)
    url_pol = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1024&height=1024&nologo=true&model=flux"
    img_data = requests.get(url_pol).content

    with open("temp.png", "wb") as f: f.write(img_data)
    
    # Assina
    img = Image.open("temp.png").convert("RGBA")
    bg = Image.new("RGBA", img.size, "WHITE")
    bg.paste(img, (0, 0), img)
    d = ImageDraw.Draw(bg)
    try: font = ImageFont.load_default()
    except: pass
    
    d.text((bg.width-200, bg.height-100), "Wen", fill="black", font=font)
    bg.convert("RGB").save("wen_art.jpg", "JPEG")
    os.remove("temp.png")
    
    # Legenda
    try: legenda = model.generate_content(f"Legenda filosófica pt-br sobre '{tema}'. #wen").text.strip()
    except: legenda = f"Arte Wen: {tema}"
    
    with open("wen_art.txt", "w", encoding="utf-8") as f: f.write(legenda)
    return legenda

def avisar_make(legenda):
    print("2. Enviando para o Make...")
    if not MAKE_WEBHOOK_URL:
        print("ERRO: Link do Make não configurado.")
        return

    # Link direto da imagem no seu site
    link_imagem = f"https://{USUARIO_GITHUB}.github.io/{NOME_REPO}/wen_art.jpg"
    
    # Envia os dados
    payload = {
        "photo_url": link_imagem,
        "caption": legenda
    }
    r = requests.post(MAKE_WEBHOOK_URL, json=payload)
    print(f"Make avisado! Código: {r.status_code}")

if __name__ == "__main__":
    legenda = criar_arte()
    avisar_make(legenda)
