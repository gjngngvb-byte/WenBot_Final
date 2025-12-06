import os
import requests
import urllib.parse
from PIL import Image, ImageDraw, ImageFont
import google.generativeai as genai
import time 
import random 
import io 

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

# Código PNG placeholder (pequeno quadrado preto) - Usado APENAS se a imagem falhar 100%
PLACEHOLDER_PNG = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00@\x00\x00\x00@\x08\x02\x00\x00\x00\x91\xe7\x04\xfb\x00\x00\x00\x06IDAT\x18\x57c\xfc\xff\x0f\x00\x06\x1a\x02\x87\x00\x00\x00\x00IEND\xaeB`\x82'

def criar_arte():
    print("1. Gerando arte...")
    
    # Lista de adjetivos para forçar a mudança de conceito na IA
    adjetivos = ["absurdo", "paradoxal", "etérea", "submerso", "cibernético", "onírico", "vintage", "vaporoso", "distópico", "utópico", "bioluminescente"]
    adjetivo_aleatorio = random.choice(adjetivos)
    
    # --- 1. IA INVENTA O TEMA (TEXTO) ---
    try:
        model = genai.GenerativeModel("gemini-2.5-flash-preview-09-2025")
        tema_prompt = f"Gere uma descrição visual {adjetivo_aleatorio}, surreal e altamente detalhada para desenho a traço. Responda APENAS a descrição em Inglês. Sem aspas."
        tema = model.generate_content(tema_prompt).text.strip()
    except: 
        tema = f"Objeto surreal {int(time.time())}" 
    
    # --- 2. GERA IMAGEM COM POLLINATIONS (COM SEED ALEATÓRIA) ---
    # A Seed aleatória garante que a imagem seja SEMPRE diferente, mesmo com o mesmo prompt.
    seed = random.randint(1, 1000000)
    
    # Prompt otimizado para o modelo Flux (usado pela Pollinations)
    prompt = f"Detailed pencil sketch, black and white line art, intricate details. Subject: {tema}. high contrast, white background." 
    
    img_data = None
    
    print(f"Tentando Pollinations com Seed {seed}...")
    try:
        safe_prompt = urllib.parse.quote(prompt)
        # Adicionamos &seed={seed} para forçar imagem única
        # Adicionamos &nologo=true para remover marca d'água se possível
        url_pol = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1024&height=1024&seed={seed}&nologo=true&model=flux"
        
        # Timeout aumentado para 30s (geração de imagem pode demorar)
        r = requests.get(url_pol, timeout=30)
        
        if r.status_code == 200 and 'image' in r.headers.get('Content-Type', ''):
             img_data = r.content
             print("✅ Imagem gerada com sucesso pelo Pollinations.")
        else:
             print(f"Pollinations falhou: {r.status_code}")
             raise Exception("Pollinations retornou erro.")
             
    except Exception as e:
        print(f"❌ Erro ao gerar desenho: {e}. Usando placeholder de emergência.")
        img_data = PLACEHOLDER_PNG
        tema = "Placeholder (Erro na geração). Tente novamente mais tarde."

    # --- SALVAR E PROCESSAR ---
    try:
        img = Image.open(io.BytesIO(img_data)).convert("RGBA")
    except:
        # Se falhar ao abrir a imagem baixada, usa o placeholder
        img = Image.open(io.BytesIO(PLACEHOLDER_PNG)).convert("RGBA")

    # Assina
    bg = Image.new("RGBA", img.size, "WHITE")
    bg.paste(img, (0, 0), img)
    d = ImageDraw.Draw(bg)
    
    # Edição da fonte
    try: 
        font = ImageFont.truetype(NOME_DO_ARQUIVO_FONTE, TAMANHO_DA_ASSINATURA) 
    except: 
        font = ImageFont.load_default()

    # Posição e texto da assinatura
    d.text((bg.width-200, bg.height-100), "Wen", fill="black", font=font)
    bg.convert("RGB").save("wen_art.jpg", "JPEG")
    
    # --- GERA A LEGENDA BASEADA NO TEMA ---
    try: 
        legenda_prompt = f"Crie uma legenda curta e filosófica em Português sobre o tema visual '{tema}'. Sem aspas. Adicione hashtags #wen #art."
        legenda = model.generate_content(legenda_prompt).text.strip()
    except: 
        legenda = f"Arte Wen: {tema} #wen #art"
    
    with open("wen_art.txt", "w", encoding="utf-8") as f: f.write(legenda)
    return legenda

def avisar_make(legenda):
    print("2. Enviando para o Make...")
    if not MAKE_WEBHOOK_URL:
        print("ERRO: Link do Make não configurado.")
        return

    # Link direto da imagem no seu site
    link_imagem = f"https://{USUARIO_GITHUB}.github.io/{NOME_REPO}/wen_art.jpg"
    
    # Envia os dados - Adiciona um parâmetro inútil (?v=time) para o Make achar que é um link novo
    link_com_cache = f"{link_imagem}?v={int(time.time())}"

    payload = {
        "photo_url": link_com_cache,
        "caption": legenda
    }
    r = requests.post(MAKE_WEBHOOK_URL, json=payload)
    print(f"Make avisado! Código: {r.status_code}")

if __name__ == "__main__":
    legenda = criar_arte()
    avisar_make(legenda)
