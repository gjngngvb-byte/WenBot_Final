import os
import requests
import urllib.parse
from PIL import Image, ImageDraw, ImageFont
import google.generativeai as genai
import time 
import random 
import io # Para lidar com dados de imagem na memória

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
REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN") # Token do Replicate

# Modelo Stable Diffusion para desenho a traço no Replicate
REPLICATE_MODEL_ID = "stability-ai/stable-diffusion:ac732df83aa6074768996774158491160fd2dc78440be58ffc6a77072e5d856d"


if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

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
        tema = f"ERROR_FALLBACK_{int(time.time() * 1000)}" 
    
    # --- 2. GERA IMAGEM COM REPLICATE API (ESTÁVEL) ---
    cache_breaker = int(time.time() * 1000) 
    
    # Prompt Completo
    prompt = f"detailed line art sketch, black pen on white paper. Subject: {tema}. high contrast, monochrome. Art Style: {cache_breaker}" 
    
    img_data = None
    
    print("Tentando Replicate API...")
    try:
        headers = {
            "Authorization": f"Token {REPLICATE_API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # O Replicate é síncrono. Tentamos gerar e buscar em uma requisição.
        response = requests.post(
            f"https://api.replicate.com/v1/predictions",
            headers=headers,
            json={
                "version": REPLICATE_MODEL_ID,
                "input": {
                    "prompt": prompt,
                    "image_dimensions": "1024x1024",
                    "num_outputs": 1,
                    "num_inference_steps": 25 # Velocidade
                }
            },
            timeout=40 # Damos mais tempo, pois a geração é lenta
        )

        if response.status_code != 201:
            raise Exception(f"Erro ao iniciar geração. Código: {response.status_code}. {response.text[:100]}")

        # O Replicate retorna um link de status, não a imagem. Precisamos do link de status.
        prediction_url = response.json().get('urls', {}).get('get')
        if not prediction_url:
             raise Exception("Não consegui obter o URL de status da predição.")

        # Polling: Espera a imagem ser gerada
        print("Aguardando geração da imagem (pode levar 20s)...")
        for _ in range(20): # Tenta 20 vezes (total 40 segundos)
            time.sleep(2)
            status_response = requests.get(prediction_url, headers=headers)
            status_data = status_response.json()

            if status_data.get('status') == 'succeeded':
                image_url = status_data.get('output')[0]
                break

            if status_data.get('status') in ['failed', 'canceled']:
                raise Exception(f"Geração falhou: {status_data.get('error')}")
        else:
             raise Exception("Timeout: Geração do Replicate demorou demais.")
        
        # Baixa a imagem gerada
        img_response = requests.get(image_url)
        if img_response.status_code == 200:
            img_data = img_response.content
            print("✅ Imagem gerada com sucesso pelo Replicate.")
        else:
            raise Exception(f"Falha ao baixar imagem. Código: {img_response.status_code}")
             
    except Exception as e:
        print(f"❌ Erro ao gerar desenho: {e}. Criando placeholder preto estável.")
        # Se falhar, cria uma imagem preta (PNG válido) que a PIL pode abrir 
        img_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00@\x00\x00\x00@\x08\x02\x00\x00\x00\x91\xe7\x04\xfb\x00\x00\x00\x06IDAT\x18\x57c\xfc\xff\x0f\x00\x06\x1a\x02\x87\x00\x00\x00\x00IEND\xaeB`\x82'
        tema = "Placeholder. Falha ao gerar desenho. #DEBUG"

    # --- SALVAR E PROCESSAR (NÃO TRAVA) ---
    img = Image.open(io.BytesIO(img_data)).convert("RGBA")
    
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
