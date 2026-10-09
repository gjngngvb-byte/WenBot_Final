# Configurar publicação direta no Instagram

O WenBot pode publicar imagens diretamente pela Instagram Graph API, sem Make.

## 1. Requisitos

- Conta Instagram profissional (Criador ou Empresa).
- App da Meta configurado para a API do Instagram e a conta corretamente vinculada.
- Token de acesso válido com permissão de publicação. Para a integração tradicional com Facebook Login, as permissões normalmente incluem `instagram_basic`, `instagram_content_publish`, `pages_show_list` e permissões de página necessárias ao tipo de token.
- A imagem precisa estar acessível publicamente por HTTPS. O fluxo usa GitHub Pages.

Os requisitos e permissões podem variar conforme o tipo de integração selecionado no Meta Developer Dashboard. Consulte a documentação oficial: https://developers.facebook.com/docs/instagram-platform/content-publishing/

## 2. Secrets no GitHub

Abra o repositório → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.

Configure:

- `IG_ACCESS_TOKEN`: token de acesso da Meta/Instagram com permissões de publicação e gerenciamento de comentários.
- `IG_USER_ID`: ID numérico da conta profissional do Instagram.
- `OPENAI_API_KEY`: chave da API OpenAI usada para arte e legendas.

O secret `MAKE_WEBHOOK_URL` deixa de ser necessário para a publicação depois que a alteração for mesclada e validada.

## 3. Variables opcionais

Em **Settings** → **Secrets and variables** → **Actions** → **Variables**, configure:

- `IG_GRAPH_VERSION`: versão suportada pela sua aplicação Meta. O código usa `v23.0` como padrão.
- `IG_USERNAME`: nome do perfil sem @, para evitar responder aos próprios comentários.
- `OPENAI_IMAGE_MODEL`: modelo de imagem disponível na sua conta.
- `OPENAI_TEXT_MODEL`: modelo de texto disponível na sua conta.

## 4. Como a publicação funciona

1. O bot gera `wen_art.jpg` e `wen_art.txt`.
2. O GitHub Actions salva os arquivos e aguarda a imagem pública no GitHub Pages.
3. O script cria um contêiner com `POST /{ig-user-id}/media`.
4. Consulta o status do contêiner.
5. Publica com `POST /{ig-user-id}/media_publish`.
6. O módulo de comentários usa o mesmo token, desde que ele tenha as permissões apropriadas.

## 5. Segurança e validação

- Nunca coloque tokens em arquivos versionados, HTML ou logs.
- Não revogue a credencial antiga antes de confirmar que o token direto funciona.
- Faça primeiro uma execução manual pelo GitHub Actions e confira o perfil antes de confiar no agendamento.
- Se a publicação falhar por permissões, conta pessoal, token vencido ou ID incorreto, corrija a configuração na Meta. O código não consegue criar permissões ou emitir um token em seu nome.
