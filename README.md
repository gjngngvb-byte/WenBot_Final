# WenBot Controller Interface

Uma interface web avançada para controlar e interagir com o WenBot - um bot de geração de arte AI que cria ilustrações únicas usando Google Gemini e Cloudflare Workers AI.

## 🚀 Funcionalidades

### Interface de Controle Aprimorada
- **Painel de parâmetros configuráveis**: Ajuste largura, altura, semente (seed), número de tentativas e seleção de modelo de IA
- **Integração com backend real**: Comunicação com servidor Flask para execução real do `robo.py`
- **Sistema de notificações toast**: Alertas visuais para início, conclusão e erros na geração
- **Logs em tempo real**: Acompanhamento detalhado do processo de geração
- **Download direto**: Baixe as artes geradas com um clique
- **Copiar para área de transferência**: Copie facilmente legendas e conceitos
- **Visualização aprimorada**: Visualização de imagem com zoom e abertura em nova aba

### Backend Flask
- **API RESTful**: Endpoints para iniciar geração, verificar status e obter resultados
- **Execução real do robo.py**: O backend executa o script original com os parâmetros fornecidos
- **Gerenciamento de processos**: Controle de processos simultâneos e captura de logs
- **Health checks**: Verificação de status do sistema e dependências

## 📁 Estrutura do Projeto

```
WenBot_Final/
├── app.py                 # Backend Flask (NOVO)
├── index.html             # Interface web aprimorada (MODIFICADO)
├── robo.py                # Script original de geração de arte
├── requirments.txt        # Dependências atualizadas (MODIFICADO)
├── wen_art.jpg            # Arte gerada atualmente
├── wen_art.txt            # Legenda da arte atual
├── wen_art_idea.txt       # Conceito/original idea
├── Quentin.otf            # Fonte usada para assinatura
├── .git/                  # Repositório Git
└── .github/               # Configurações do GitHub
```

## 🔧 Como Usar

### Pré-requisitos
1. **Python 3.8+** instalado e disponível no PATH
2. **API Keys configuradas** como variáveis de ambiente:
   - `GOOGLE_API_KEY` - Para acesso ao Google Gemini
   - `CLOUDFLARE_ACCOUNT_ID` - Para Cloudflare Workers AI
   - `CLOUDFLARE_API_TOKEN` - Para Cloudflare Workers AI
3. **Dependências Python** instaladas:
   ```bash
   pip install -r requirements.txt
   ```

### Execução
1. **Inicie o backend**:
   ```bash
   python app.py
   ```
   O servidor estará disponível em `http://localhost:5000`

2. **Acesse a interface**:
   Abra seu navegador e vá para `http://localhost:5000`

3. **Configure os parâmetros** no painel de controle:
   - Largura/Altura: 256-2048 pixels
   - Semente (opcional): Para resultados reproduzíveis
   - Modelo: Selecione o modelo de IA desejado
   - Tentativas: Número de tentativas em caso de falha

4. **Gerar arte**:
   Clique em "🚀 Gerar Nova Arte" para iniciar o processo
   - Acompanhe o progresso nos logs e notificações
   - Visualize a arte gerada assim que estiver pronta
   - Baixe ou copie legenda/conceito conforme necessário

## 📝 Notas Importantes

### Modo Simulação
Se o backend não estiver disponível ou se houver credenciais ausentes, a interface automaticamente muda para **modo simulação**, onde:
- O processo de geração é simulado com delays realistas
- Conteúdo de demonstração é gerado para visualização
- Notificações informam que está em modo simulação
- Isso permite testar a interface mesmo sem API keys ou Python

### Variáveis de Ambiente
Certifique-se de definir as seguintes variáveis antes de executar o backend:
```bash
# Linux/Mac
export GOOGLE_API_KEY="sua_chave_aqui"
export CLOUDFLARE_ACCOUNT_ID="seu_id_aqui"
export CLOUDFLARE_API_TOKEN="seu_token_aqui"

# Windows (cmd)
set GOOGLE_API_KEY=sua_chave_aqui
set CLOUDFLARE_ACCOUNT_ID=seu_id_aqui
set CLOUDFLARE_API_TOKEN=seu_token_aqui

# Windows (PowerShell)
$env:GOOGLE_API_KEY="sua_chave_aqui"
$env:CLOUDFLARE_ACCOUNT_ID="seu_id_aqui"
$env:CLOUDFLARE_API_TOKEN="seu_token_aqui"
```

## 🛠️ Tecnologias Utilizadas

- **Frontend**: HTML5, CSS3, Vanilla JavaScript (ES6+)
- **Backend**: Python Flask
- **Comunicação**: REST API com JSON
- **Estilização**: CSS moderno com variáveis, flexbox e grid
- **Animações**: CSS transitions e keyframes
- **Armazenamento temporário**: LocalStorage (para state da interface)

## 🔄 Fluxo de Funcionamento

1. Usuário configura parâmetros na interface
2. Ao clicar em "Gerar Nova Arte":
   - Frontend valida os parâmetros
   - Envia requisição POST para `/api/generate` com os parâmetros
   - Backend recebe e inicia o `robo.py` como subprocesso
   - Backend captura stdout/stderr em tempo real
   - Frontend polling periódico para `/api/status/{process_id}`
   - Quando concluído, frontend busca `/api/art` para atualizar display
   - Notificações toast informam o usuário em cada etapa

## 📤 Upload para GitHub

Este repositório já está configurado como um repositório Git. Para enviar suas alterações:

```bash
# Adicionar todos os arquivos novos/modificados
git add .

# Commit com mensagem descritiva
git commit -m "Adicionar interface de controle avançada e backend Flask para WenBot"

# Push para o repositório remoto
git push origin main
```

## 🎯 Próximos Passos Sugeridos

1. **WebSocket para logs em tempo real**: Substituir polling por conexão WebSocket para atualizações instantâneas
2. **Histórico de gerações**: Armazenar e exibir versões anteriores das artes
3. **Comparação lado a lado**: Visualizar duas gerações simultaneamente para comparação
4. **Configurações salvas**: Persistir parâmetros preferidos no localStorage
5. **Modo escuro/claro**: Tema alternativo baseado na preferência do sistema
6. **Integração com redes sociais**: Botões para compartilhar diretamente no Instagram/Twitter

---

**Nota**: Esta interface foi desenvolvida para aprimorar a experiência de uso do WenBot, mantendo compatibilidade total com o script original `robo.py`. Todas as artes geradas continua sendo produzidas pelo mesmo processo de alta qualidade, apenas com mais controle e visibilidade para o usuário.

Desenvolvido com ❤️ usando WenBot.