import base64
import io
import os
import random
from pathlib import Path

from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont

USUARIO_GITHUB = "gjngngvb-byte"
NOME_REPO = "WenBot_Final"
NOME_DO_ARQUIVO_FONTE = "Quentin.otf"
TAMANHO_DA_ASSINATURA = 60
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_IMAGE_MODEL = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1")
OPENAI_TEXT_MODEL = os.environ.get("OPENAI_TEXT_MODEL", "gpt-4.1-mini")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY não configurada nos Secrets do GitHub.")

client = OpenAI(api_key=OPENAI_API_KEY)

ASSUNTOS = [
    "um animal impossível que mistura duas criaturas sem relação",
    "um objeto cotidiano se comportando como um ser vivo",
    "uma máquina estranha com uma finalidade impossível",
    "um edifício surreal que não poderia existir no mundo real",
    "um personagem misterioso feito de um material inesperado",
    "uma mistura de natureza com tecnologia avançada",
    "um objeto futurista de uma civilização desconhecida",
    "uma cena submarina impossível",
    "um objeto comum que contém um mundo em miniatura",
    "um objeto gigantesco visto da perspectiva de algo minúsculo",
    "um mundo minúsculo escondido dentro de um objeto comum",
    "um veículo impossível atravessando uma rua comum",
    "um organismo botânico bizarro com detalhes mecânicos",
    "uma criatura surreal aparecendo em um lugar cotidiano",
    "uma cidade onírica com um único elemento fisicamente impossível",
]

ANGULOS = [
    "vista aérea extrema", "vista de baixo extrema",
    "perspectiva dramática de baixo para cima",
    "perspectiva dramática de cima para baixo",
    "perspectiva diagonal acentuada",
    "macro com profundidade exagerada",
    "vista de três quartos com forte escorço",
    "perspectiva totalmente de cima",
    "vista lateral com profundidade incomum",
    "perspectiva extrema de uma posição impossível",
]

def gerar_ideia():
    prompt = f"""
Crie UMA ideia visual original para uma ilustração surreal desenhada com caneta preta.
Conceito-base: {random.choice(ASSUNTOS)}
Câmera/composição: {random.choice(ANGULOS)}
A ideia deve ser visualmente clara, estranha e inesperada, sem clichês genéricos de fantasia.
Retorne apenas a descrição visual em português, com no máximo 150 palavras.
""".strip()
    resposta = client.responses.create(model=OPENAI_TEXT_MODEL, input=prompt)
    texto = (resposta.output_text or "").strip()
    if not texto:
        raise RuntimeError("A API OpenAI não retornou uma ideia.")
    return texto[:1800]

def baixar_imagem(prompt):
    print(f"Gerando imagem com {OPENAI_IMAGE_MODEL}...")
    resultado = client.images.generate(
        model=OPENAI_IMAGE_MODEL,
        prompt=prompt,
        size="1024x1024",
        quality="medium",
        n=1,
    )
    dados = resultado.data[0].b64_json
    if not dados:
        raise RuntimeError("A API OpenAI não retornou os dados da imagem.")
    imagem = Image.open(io.BytesIO(base64.b64decode(dados))).convert("RGB")
    if imagem.width < 100 or imagem.height < 100:
        raise RuntimeError("A imagem retornada é inválida.")
    return imagem

def salvar_arte(img):
    fundo = img.convert("RGB")
    d = ImageDraw.Draw(fundo)
    try:
        fonte = ImageFont.truetype(NOME_DO_ARQUIVO_FONTE, TAMANHO_DA_ASSINATURA)
    except Exception:
        fonte = ImageFont.load_default()
    texto = "Wen"
    box = d.textbbox((0, 0), texto, font=fonte)
    d.text((fundo.width-(box[2]-box[0])-35, fundo.height-(box[3]-box[1])-35), texto, fill="black", font=fonte)
    fundo.save("wen_art.jpg", "JPEG", quality=95)

def analisar_imagem_e_criar_legenda():
    print("Analisando a imagem final com OpenAI...")
    imagem = Image.open("wen_art.jpg").convert("RGB")
    buffer = io.BytesIO()
    imagem.save(buffer, format="JPEG", quality=90)
    import base64
    imagem_data = base64.b64encode(buffer.getvalue()).decode("ascii")
    prompt = """
Analise ESTA IMAGEM REAL, não apenas a ideia original.
Escreva uma legenda pronta para Instagram em português brasileiro.
Descreva somente o que está visível. Considere assunto, ação, perspectiva incomum,
composição, atmosfera e detalhes surreais. Seja humano, intrigante e levemente poético.
No máximo 4 linhas curtas antes das hashtags. Não invente detalhes.
Nunca mencione IA, OpenAI, prompts, automação ou geração de imagens.
Finalize com exatamente 5 hashtags relevantes, incluindo sempre #wen e #art.
Coloque as hashtags na última linha. Retorne somente a legenda final.
""".strip()
    resposta = client.responses.create(
        model=OPENAI_TEXT_MODEL,
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt},
                {"type": "input_image", "image_url": f"data:image/jpeg;base64,{imagem_data}"},
            ],
        }],
    )
    legenda = (resposta.output_text or "").strip()
    if not legenda or "#wen" not in legenda.lower() or "#art" not in legenda.lower():
        raise RuntimeError("Não foi possível criar uma legenda válida com #wen e #art.")
    return legenda

def criar_arte():
    ideia = gerar_ideia()
    print(f"Conceito: {ideia}")
    prompt = f"""
Ilustração feita à mão com caneta de tinta preta em papel branco limpo.

CONCEITO VISUAL:
{ideia}

ESTILO OBRIGATÓRIO:
somente tinta preta, traços expressivos de caneta, linhas finas com pesos variados,
espaço negativo branco, ilustração artística surreal, ângulo de câmera incomum,
perspectiva dinâmica, composição forte, silhueta clara e hachuras desenhadas à mão.
A imagem deve parecer uma ilustração física feita por um artista, não um render digital.

EVITAR:
cores, fotorrealismo, render 3D, pintura, aquarela, lápis de cor,
gradientes digitais cinzentos, texto, logos, moldura ou borda.
Não desenhe assinatura ou letras, pois a assinatura será adicionada depois.
""".strip()
    img = baixar_imagem(prompt)
    salvar_arte(img)
    legenda = analisar_imagem_e_criar_legenda()
    Path("wen_art.txt").write_text(legenda + "\n", encoding="utf-8")
    Path("wen_art_idea.txt").write_text(ideia + "\n", encoding="utf-8")
    print(legenda)
    return legenda

if __name__ == "__main__":
    criar_arte()
