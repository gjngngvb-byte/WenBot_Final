import os
import random
import requests
import base64
import json
import urllib.parse
from PIL import Image, ImageDraw, ImageFont
import google.generativeai as genai
from instagrapi import Client

# Configurações e Segredos
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
INSTA_USER = os.environ.get("INSTA_USER")
INSTA_PASS = os.environ.get("INSTA_PASS")
INSTA_SETTINGS = os.environ.get("INSTA_SETTINGS")

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

def log(msg):
    print(f"[WEN BOT] {msg}")

def criar_arte():
    log("1. Inventando tema...")
    try:
        model = genai.GenerativeModel("gemini-2.5-flash-preview-09-2025")
        tema = model.generate_content("Gere uma ideia visual surreal e criativa para desenho a traço. Responda APENAS o sujeito em Inglês.").text.strip()
    except:
        tema = "A clock melting on a tree"
    
    log(f"Tema: {tema}")
    
    # Prompt Estilo Caneta Preta
    prompt = f"Hand-drawn black ballpoint pen sketch on clean white paper. Subject: {tema}. intricate details, high contrast, scribble style."
    
    img_data = None
    try:
        # Tenta Google Imagen
        url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-4.0-generate-001:predict?key={GOOGLE_API_KEY}"
        resp = requests.post(url, json={"instances": [{"prompt": prompt}], "parameters": {"sampleCount": 1}})
        if resp.status_code == 200:
            b64 = resp.json()['predictions'][0]['bytesBase64Encoded']
            img_data = base64.b64decode(b64)
    except: pass

    if not img_data:
        # Fallback Pollinations
        log("Usando gerador backup...")
        safe_prompt = urllib.parse.quote(prompt)
        url_pol = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1024&height=1024&nologo=true&model=flux"
        img_data = requests.get(url_pol).content

    with open("temp.png", "wb") as f: f.write(img_data)
    
    img = Image.open("temp.png").convert("RGBA")
    bg = Image.new("RGBA", img.size, "WHITE")
    bg.paste(img, (0, 0), img)
    
    d = ImageDraw.Draw(bg)
    try: font = ImageFont.truetype("arial.ttf", 80)
    except: font = ImageFont.load_default()
    
    d.text((bg.width-220, bg.height-150), "Wen", fill="black", font=font)
    bg.convert("RGB").save("wen_art.jpg", "JPEG")
    os.remove("temp.png")
    
    try:
        legenda = model.generate_content(f"Crie uma legenda curta e filosófica em Português sobre '{tema}'. Sem aspas. Adicione hashtags #wen #art.").text.strip()
    except:
        legenda = f"Arte sobre {tema}. #wen #art"
        
    with open("wen_art.txt", "w", encoding="utf-8") as f: f.write(legenda)
    return "wen_art.jpg", legenda

def postar(arquivo, legenda):
    log("3. Postando no Instagram...")
    cl = Client()
    
    try:
        # Tenta usar a sessão salva para evitar bloqueio
        if INSTA_SETTINGS:
            log("Carregando sessão salva...")
            settings = json.loads(INSTA_SETTINGS)
            cl.set_settings(settings)
            cl.login(INSTA_USER, INSTA_PASS)
        else:
            cl.login(INSTA_USER, INSTA_PASS)
            
        cl.photo_upload(arquivo, caption=legenda)
        log("✅ SUCESSO! Postado no Instagram.")
    except Exception as e:
        log(f"❌ Erro ao postar: {e}")

if __name__ == "__main__":
    try:
        arquivo, legenda = criar_arte()
        postar(arquivo, legenda)
    except Exception as e:
        log(f"Erro fatal: {e}")
