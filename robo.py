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

# Lista de backup MÍNIMA apenas para não travar se a API do Google cair 100%
FALLBACK_SIMPLE = "A giant ancient tree floating in void"

def criar_arte():
    print("1. Gerando arte...")
    
    tema_escolhido = ""
    
    # --- 1. GEMINI COMO GERADOR DE PROMPTS INFINITOS ---
    try:
        model = genai.GenerativeModel("gemini-2.5-flash-preview-09-2025")
        
        # Esta é a "Semente da Loucura". Pedimos para ele ser aleatório.
        # Temperatura alta (se pudesse configurar) ajuda, mas o prompt resolve.
        instrucao_criativa = (
            "Atue como um gerador de ideias artísticas vanguardista e aleatório. "
            "Gere uma descrição visual ÚNICA, SURREAL e INESPERADA para um desenho a traço. "
            "Misture conceitos distantes (ex: natureza + máquinas, espaço + fundo do mar, antigo + cyberpunk). "
            "NÃO use clichês como 'relógio derretendo'. Seja bizarro e poético. "
            "Responda APENAS a descrição do objeto/cena em Inglês."
        )
        
        tema_escolhido = model.generate_content(instrucao_criativa).text.strip()
        
        # Limpeza básica caso ele seja muito verborrágico
        if len(tema_escolhido) > 300: 
            tema_escolhido = tema_escolhido[:300]
            
        print(f"✨ Gemini imaginou: {tema_escolhido}")
        
    except Exception as e:
        print(f"Erro no Gemini: {e}. Usando fallback simples.")
        tema_escolhido = FALLBACK_SIMPLE

    # --- 2. GERA IMAGEM COM POLLINATIONS ---
    # A Seed continua aleatória para garantir que o traço mude mesmo se o tema for similar
    seed = random.randint(1, 9999999) 
    
    # Prompt de Estilo Fixo (O "Traço Wen") + A Ideia Maluca do Gemini
    prompt_imagem = f"Detailed black pencil sketch, masterpiece, rough sketch style, charcoal lines on white paper. Subject: {tema_escolhido}. high contrast, white background, single isolated object." 
    
    img_data = None
    
    try:
        safe_prompt = urllib.parse.quote(prompt_imagem)
        # Pollinations com modelo FLUX (Melhor para seguir instruções complexas)
        url_pol = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1024&height=1024&seed={seed}&nologo=true&model=flux"
        
        r = requests.get(url_pol, timeout=45) 
        
        if r.status_code == 200 and 'image' in r.headers.get('Content-Type', ''):
             img_data = r.content
        else:
             raise Exception(f"Erro imagem: {r.status_code}")
             
    except Exception as e:
        print(f"❌ Falha crítica: {e}")
        # Placeholder de emergência (para não parar o bot)
        img_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00@\x00\x00\x00@\x08\x02\x00\x00\x00\x91\xe7\x04\xfb\x00\x00\x00\x06IDAT\x18\x57c\xfc\xff\x0f\x00\x06\x1a\x02\x87\x00\x00\x00\x00IEND\xaeB`\x82'
        tema_escolhido = "Erro técnico momentâneo."

    # --- SALVAR E PROCESSAR ---
    try:
        img = Image.open(io.BytesIO(img_data)).convert("RGBA")
    except:
        img = Image.open(io.BytesIO(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00@\x00\x00\x00@\x08\x02\x00\x00\x00\x91\xe7\x04\xfb\x00\x00\x00\x06IDAT\x18\x57c\xfc\xff\x0f\x00\x06\x1a\x02\x87\x00\x00\x00\x00IEND\xaeB`\x82')).convert("RGBA")

    # Assina
    bg = Image.new("RGBA", img.size, "WHITE")
    bg.paste(img, (0, 0), img)
    d = ImageDraw.Draw(bg)
    
    try: font = ImageFont.truetype(NOME_DO_ARQUIVO_FONTE, TAMANHO_DA_ASSINATURA) 
    except: font = ImageFont.load_default()

    d.text((bg.width-200, bg.height-100), "Wen", fill="black", font=font)
    bg.convert("RGB").save("wen_art.jpg", "JPEG")
    
    # --- GERA A LEGENDA ---
    try: 
        # Pede para o Gemini explicar a loucura que ele criou
        legenda_prompt = f"Crie uma legenda curta, profunda e poética em Português para esta obra de arte: '{tema_escolhido}'. Use um tom artístico. Adicione #wen #art."
        legenda = model.generate_content(legenda_prompt).text.strip()
    except: 
        legenda = f"Arte Wen: {tema_escolhido} #wen #art"
    
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
