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

# Lista de backup MÍNIMA
FALLBACK_SIMPLE = "A giant ancient tree floating in void"

def criar_arte():
    print("1. Gerando arte...")
    
    tema_escolhido = ""
    
    # --- 1. GEMINI COMO GERADOR DE PROMPTS INFINITOS ---
    try:
        model = genai.GenerativeModel("gemini-2.5-flash-preview-09-2025")
        
        instrucao_criativa = (
            "Atue como um gerador de ideias artísticas vanguardista e aleatório. "
            "Gere uma descrição visual ÚNICA, SURREAL e INESPERADA para um desenho a traço. "
            "Misture conceitos distantes (ex: natureza + máquinas, espaço + fundo do mar). "
            "NÃO use clichês. Seja bizarro e poético. "
            "Responda APENAS a descrição do objeto/cena em Inglês."
        )
        
        tema_escolhido = model.generate_content(instrucao_criativa).text.strip()
        if len(tema_escolhido) > 300: tema_escolhido = tema_escolhido[:300]
        print(f"✨ Gemini imaginou: {tema_escolhido}")
        
    except Exception as e:
        print(f"Erro no Gemini: {e}. Usando fallback.")
        tema_escolhido = FALLBACK_SIMPLE

    # --- 2. GERA IMAGEM COM POLLINATIONS ---
    seed = random.randint(1, 9999999) 
    prompt_imagem = f"Detailed black pencil sketch, masterpiece, rough sketch style, charcoal lines on white paper. Subject: {tema_escolhido}. high contrast, white background, single isolated object." 
    
    img_data = None
    
    try:
        safe_prompt = urllib.parse.quote(prompt_imagem)
        url_pol = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1024&height=1024&seed={seed}&nologo=true&model=flux"
        r = requests.get(url_pol, timeout=45) 
        if r.status_code == 200 and 'image' in r.headers.get('Content-Type', ''):
             img_data = r.content
        else:
             raise Exception(f"Erro imagem: {r.status_code}")
    except Exception as e:
        print(f"❌ Falha crítica: {e}")
        img_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00@\x00\x00\x00@\x08\x02\x00\x00\x00\x91\xe7\x04\xfb\x00\x00\x00\x06IDAT\x18\x57c\xfc\xff\x0f\x00\x06\x1a\x02\x87\x00\x00\x00\x00IEND\xaeB`\x82'
        tema_escolhido = "Erro técnico momentâneo."

    # --- SALVAR E PROCESSAR ---
    try: img = Image.open(io.BytesIO(img_data)).convert("RGBA")
    except: img = Image.open(io.BytesIO(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00@\x00\x00\x00@\x08\x02\x00\x00\x00\x91\xe7\x04\xfb\x00\x00\x00\x06IDAT\x18\x57c\xfc\xff\x0f\x00\x06\x1a\x02\x87\x00\x00\x00\x00IEND\xaeB`\x82')).convert("RGBA")

    bg = Image.new("RGBA", img.size, "WHITE")
    bg.paste(img, (0, 0), img)
    d = ImageDraw.Draw(bg)
    try: font = ImageFont.truetype(NOME_DO_ARQUIVO_FONTE, TAMANHO_DA_ASSINATURA) 
    except: font = ImageFont.load_default()
    d.text((bg.width-200, bg.height-100), "Wen", fill="black", font=font)
    bg.convert("RGB").save("wen_art.jpg", "JPEG")
    
    # --- 3. GERA A LEGENDA CONTEXTUAL ---
    print("3. Criando legenda contextual...")
    try: 
        instrucao_legenda = (
            f"Escreva uma legenda poética em Português do Brasil SOBRE este tema visual específico: '{tema_escolhido}'.\n"
            "Atenção: A legenda deve refletir a atmosfera da imagem. Se for sombria, seja sombrio. Se for mágica, seja mágico. Se for tecnológica, fale sobre futuro/máquinas.\n"
            "Estilo: Curto, profundo, máximo 4 linhas.\n"
            "Final: Crie 3 hashtags em Português que descrevam EXATAMENTE o objeto da imagem (ex: se for robô use #robo #futuro), e termine com #wen #art.\n"
            "NÃO use aspas."
        )
        legenda = model.generate_content(instrucao_legenda).text.strip()
    except: 
        legenda = f"Arte Wen: {tema_escolhido} \n#wen #art"
    
    with open("wen_art.txt", "w", encoding="utf-8") as f: f.write(legenda)
    return legenda

def avisar_make(legenda):
    print("2. Enviando para o Make...")
    if not MAKE_WEBHOOK_URL:
        print("ERRO: Link do Make não configurado.")
        return

    link_imagem = f"https://{USUARIO_GITHUB}.github.io/{NOME_REPO}/wen_art.jpg?v={int(time.time())}"
    
    payload = {
        "photo_url": link_imagem,
        "caption": legenda
    }
    r = requests.post(MAKE_WEBHOOK_URL, json=payload)
    print(f"Make avisado! Código: {r.status_code}")

if __name__ == "__main__":
    legenda = criar_arte()
    avisar_make(legenda)
