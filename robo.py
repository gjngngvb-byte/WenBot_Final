import os
import requests
import urllib.parse
from PIL import Image, ImageDraw, ImageFont
import google.generativeai as genai
import time 
import random 
import base64 

# --- CONFIGURAÇÕES (PREENCHA AQUI) ---
NOME_DO_ARQUIVO_FONTE = "Quentin.otf" 
TAMANHO_DA_ASSINATURA = 60         
# -------------------------------------

# Exemplo: se seu site é gjngngvb-byte.github.io/WenBot_Final
USUARIO_GITHUB = "gjngngvb-byte"  
NOME_REPO = "WenBot_Final"      

# Segredos
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
MAKE_WEBHOOK_URL = os.environ.get("MAKE_WEBHOOK_URL")

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

def criar_arte():
    print("1. Gerando arte...")
    
    # Lista de adjetivos para forçar a mudança de conceito na IA
    adjetivos = ["absurdo", "paradoxal", "etérea", "submerso", "cibernético", "onírico", "vintage", "vaporoso", "distópico", "utópico", "bioluminescente"]
    adjetivo_aleatorio = random.choice(adjetivos)
    
    # --- 1. IA INVENTA O TEMA ---
    try:
        model = genai.GenerativeModel("gemini-2.5-flash-preview-09-2025")
        tema_prompt = f"Gere uma descrição visual {adjetivo_aleatorio}, surreal e altamente detalhada para desenho a traço. Responda APENAS a descrição em Inglês. Sem aspas."
        tema = model.generate_content(tema_prompt).text.strip()
    except: 
        tema = f"ERROR_FALLBACK_{int(time.time() * 1000)}" 
    
    # --- 2. GERA IMAGEM USANDO GEMINI IMAGE API (ESTÁVEL) ---
    cache_breaker = int(time.time() * 1000) 
    
    # Prompt Completo para a Geração de Imagem
    prompt = f"CacheID:{cache_breaker}. Hand-drawn black ballpoint pen sketch on clean white paper. Subject: {tema}. intricate details, high contrast, scribble style." 
    
    img_data = None
    
    print("Tentando Gemini Image Generation...")
    try:
        # Usamos o mesmo modelo de texto para gerar a imagem.
        # Isso deve funcionar com a chave existente.
        image_model = genai.GenerativeModel("gemini-2.5-flash-image-preview")
        
        response = image_model.generate_content(
            contents=prompt,
            config={
                "response_mime_type": "image/jpeg",
                "response_schema": {
                    "type": "object",
                    "properties": {
                        "image": {"type": "string", "format": "byte"}
                    }
                }
            }
        )
        
        # A resposta da API da Google é um JSON. Pegamos o base64
        b64 = response.candidates[0].content.parts[0].text
        img_data = base64.b64decode(b64)
        print("✅ Imagem gerada com sucesso pelo Gemini Image.")
            
    except Exception as e:
        print(f"❌ Erro ao chamar Gemini Image: {e}. Criando placeholder preto.")
        # Se falhar, cria uma imagem preta para evitar o erro de arquivo (travar a PIL)
        img_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00@\x00\x00\x00@\x08\x02\x00\x00\x00\x91\xe7\x04\xfb\x00\x00\x00\x06IDAT\x18\x57c\xfc\xff\x0f\x00\x06\x1a\x02\x87\x00\x00\x00\x00IEND\xaeB`\x82'
        tema = "Placeholder. Failed to generate image."

    # --- SALVAR E PROCESSAR (AGORA TEMOS CERTEZA QUE img_data É UMA IMAGEM VÁLIDA) ---
    with open("temp.png", "wb") as f: f.write(img_data)
    
    # A linha que estava falhando antes (Linha 56)
    img = Image.open("temp.png").convert("RGBA") 
    
    # Assina
    bg = Image.new("RGBA", img.size, "WHITE")
    bg.paste(img, (0, 0), img)
    d = ImageDraw.Draw(bg)
    
    # Edição da fonte
    try: 
        font = ImageFont.truetype(NOME_DO_ARQUIVO_FONTE, TAMANHO_DA_ASSINATURA) 
        print(f"Fonte {NOME_DO_ARQUIVO_FONTE} carregada.")
    except Exception as e: 
        font = ImageFont.load_default()
        print(f"Erro ao carregar fonte personalizada: {e}. Usando fonte padrão.")

    # Posição e texto da assinatura
    d.text((bg.width-200, bg.height-100), "Wen", fill="black", font=font)
    bg.convert("RGB").save("wen_art.jpg", "JPEG")
    os.remove("temp.png")
    
    # --- GERA A LEGENDA BASEADA NO TEMA ---
    try: 
        legenda_prompt = f"Crie uma legenda curta e filosófica em Português sobre o tema visual '{tema}'. Sem aspas. Adicione hashtags #wen #art."
        legenda = model.generate_content(legenda_prompt).text.strip()
    except: 
        legenda = f"Arte Wen: {tema}"
    
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
