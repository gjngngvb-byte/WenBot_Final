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
        body: JSON.stringify({ ref: "main" })
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
