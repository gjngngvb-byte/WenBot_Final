const ALLOWED_ORIGINS = new Set([
  "https://gjngngvb-byte.github.io",
  "https://wenbot-trigger.netlify.app"
]);

function responseJson(data, status, origin) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "access-control-allow-origin": origin || "https://gjngngvb-byte.github.io",
      "access-control-allow-methods": "POST, OPTIONS",
      "access-control-allow-headers": "content-type",
      "vary": "Origin",
      "cache-control": "no-store"
    }
  });
}

export default async (request) => {
  const origin = request.headers.get("origin") || "";
  const allowedOrigin = ALLOWED_ORIGINS.has(origin) ? origin : "";

  if (request.method === "OPTIONS") {
    if (!allowedOrigin) return new Response(null, { status: 403 });
    return new Response(null, {
      status: 204,
      headers: {
        "access-control-allow-origin": allowedOrigin,
        "access-control-allow-methods": "POST, OPTIONS",
        "access-control-allow-headers": "content-type",
        "access-control-max-age": "600",
        "vary": "Origin"
      }
    });
  }

  if (request.method !== "POST") {
    return responseJson({ error: "Método não permitido." }, 405, allowedOrigin);
  }
  if (!allowedOrigin) {
    return responseJson({ error: "Origem não autorizada." }, 403, "https://gjngngvb-byte.github.io");
  }

  const expectedPassword = Netlify.env.get("WENBOT_TRIGGER_PASSWORD");
  const githubToken = Netlify.env.get("GITHUB_ACTIONS_TOKEN");
  if (!expectedPassword || !githubToken) {
    return responseJson({ error: "A integração ainda não foi configurada no Netlify." }, 503, allowedOrigin);
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return responseJson({ error: "Pedido inválido." }, 400, allowedOrigin);
  }

  if (typeof body.password !== "string" || body.password.length < 1 || body.password !== expectedPassword) {
    return responseJson({ error: "Senha de acionamento incorreta." }, 401, allowedOrigin);
  }

  const action = typeof body.action === "string" ? body.action : "publish";
  const allowedActions = new Set(["publish", "hashtag_comments", "reply_comments", "set_social_pause"]);
  if (!allowedActions.has(action)) {
    return responseJson({ error: "Tarefa solicitada inválida." }, 400, allowedOrigin);
  }

  if (action === "set_social_pause") {
    const controlKeys = {
      hashtag_comments: "pause_hashtag_comments",
      reply_comments: "pause_reply_comments"
    };
    const key = controlKeys[body.control];
    if (!key || typeof body.paused !== "boolean") {
      return responseJson({ error: "Controle de pausa inválido." }, 400, allowedOrigin);
    }

    const path = "wenbot_social_controls.json";
    const apiUrl = "https://api.github.com/repos/gjngngvb-byte/WenBot_Final/contents/" + path;
    const headers = {
      "accept": "application/vnd.github+json",
      "authorization": `Bearer ${githubToken}`,
      "x-github-api-version": "2022-11-28",
      "content-type": "application/json",
      "user-agent": "WenBot-Netlify-Trigger"
    };
    try {
      const currentResponse = await fetch(apiUrl + "?ref=main", { headers });
      if (!currentResponse.ok) {
        const details = await currentResponse.text();
        console.error("Could not read social controls:", currentResponse.status, details.slice(0, 300));
        return responseJson({
          error: currentResponse.status === 401 || currentResponse.status === 403
            ? "O token do GitHub precisa de permissão Contents: read and write para controlar as pausas."
            : "Não foi possível ler o estado atual das pausas no GitHub."
        }, 502, allowedOrigin);
      }
      const current = await currentResponse.json();
      let state;
      try {
        state = JSON.parse(decodeURIComponent(escape(atob(current.content.replace(/\s/g, "")))));
      } catch {
        state = { pause_hashtag_comments: true, pause_reply_comments: true };
      }
      state.pause_hashtag_comments = state.pause_hashtag_comments !== false;
      state.pause_reply_comments = state.pause_reply_comments !== false;
      state[key] = body.paused;

      const encoded = btoa(unescape(encodeURIComponent(JSON.stringify(state, null, 2) + "\n")));
      const saveResponse = await fetch(apiUrl, {
        method: "PUT",
        headers,
        body: JSON.stringify({
          message: (body.paused ? "Pausar " : "Retomar ") + (body.control === "hashtag_comments" ? "comentários por hashtag" : "respostas a comentários"),
          content: encoded,
          sha: current.sha,
          branch: "main"
        })
      });
      if (!saveResponse.ok) {
        const details = await saveResponse.text();
        console.error("Could not save social controls:", saveResponse.status, details.slice(0, 300));
        return responseJson({
          error: saveResponse.status === 401 || saveResponse.status === 403
            ? "O token do GitHub precisa de permissão Contents: read and write para salvar as pausas."
            : "O GitHub não conseguiu salvar o controle de pausa."
        }, 502, allowedOrigin);
      }
      return responseJson({
        ok: true,
        message: (body.paused ? "Função pausada: " : "Função retomada: ") + (body.control === "hashtag_comments" ? "comentários em posts." : "respostas a comentários."),
        state
      }, 200, allowedOrigin);
    } catch (error) {
      console.error("Social pause update failed:", error);
      return responseJson({ error: "Não foi possível salvar o controle de pausa no GitHub." }, 502, allowedOrigin);
    }
  }

  const params = body.params && typeof body.params === "object" ? body.params : {};
  const width = Number(params.width ?? 1024);
  const height = Number(params.height ?? 1024);
  const attempts = Number(params.attempts ?? 3);
  const seed = params.seed === null || params.seed === undefined || params.seed === ""
    ? ""
    : String(params.seed);
  const model = params.model ?? "@cf/black-forest-labs/flux-2-klein-9b";
  const allowedModels = new Set([
    "@cf/black-forest-labs/flux-2-klein-9b",
    "@cf/black-forest-labs/flux-1-schnell"
  ]);

  if (!Number.isInteger(width) || width < 256 || width > 2048 ||
      !Number.isInteger(height) || height < 256 || height > 2048) {
    return responseJson({ error: "Largura e altura devem ficar entre 256 e 2048 pixels." }, 400, allowedOrigin);
  }
  if (!Number.isInteger(attempts) || attempts < 1 || attempts > 10) {
    return responseJson({ error: "As tentativas devem ficar entre 1 e 10." }, 400, allowedOrigin);
  }
  if (seed !== "" && (!/^\d+$/.test(seed) || Number(seed) > 999999999)) {
    return responseJson({ error: "A semente deve ser um inteiro entre 0 e 999999999." }, 400, allowedOrigin);
  }
  if (!allowedModels.has(model)) {
    return responseJson({ error: "Modelo de imagem inválido." }, 400, allowedOrigin);
  }

  try {
    const githubResponse = await fetch(
      "https://api.github.com/repos/gjngngvb-byte/WenBot_Final/actions/workflows/wen_action.yml/dispatches",
      {
        method: "POST",
        headers: {
          "accept": "application/vnd.github+json",
          "authorization": `Bearer ${githubToken}`,
          "x-github-api-version": "2022-11-28",
          "content-type": "application/json",
          "user-agent": "WenBot-Netlify-Trigger"
        },
        body: JSON.stringify({
          ref: "main",
          inputs: {
            action,
            width: String(width),
            height: String(height),
            seed,
            model,
            attempts: String(attempts)
          }
        })
      }
    );

    if (!githubResponse.ok) {
      const details = await githubResponse.text();
      console.error("GitHub workflow dispatch failed:", githubResponse.status, details.slice(0, 500));
      return responseJson({
        error: githubResponse.status === 401 || githubResponse.status === 403
          ? "O token do GitHub não tem as permissões necessárias."
          : "O GitHub não aceitou iniciar o workflow.",
        github_status: githubResponse.status
      }, 502, allowedOrigin);
    }

    return responseJson({
      ok: true,
      message: "Workflow iniciado. A geração pode levar alguns minutos.",
      workflow_url: "https://github.com/gjngngvb-byte/WenBot_Final/actions/workflows/wen_action.yml"
    }, 200, allowedOrigin);
  } catch (error) {
    console.error("WenBot trigger error:", error);
    return responseJson({ error: "Não foi possível contactar o GitHub." }, 502, allowedOrigin);
  }
};
