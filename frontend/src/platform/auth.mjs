import {
  InMemoryWebStorage,
  UserManager,
  WebStorageStateStore,
} from "oidc-client-ts";

let initialization;
export function authentication(api) {
  if (!initialization)
    initialization = initialize(api).catch((error) => {
      initialization = null;
      throw error;
    });
  return initialization;
}
async function initialize(api) {
  const config = await api.request("/auth/config");
  if (config.mode === "demo" && config.simulated === true)
    return { config, manager: null, user: null };
  if (config.mode !== "oidc" || !config.client_id)
    throw new Error("Unsupported authentication configuration");
  const issuer = new URL(config.issuer);
  if (
    issuer.username ||
    issuer.password ||
    issuer.search ||
    issuer.hash ||
    (issuer.protocol !== "https:" &&
      !(
        issuer.protocol === "http:" &&
        ["127.0.0.1", "localhost"].includes(issuer.hostname)
      ))
  )
    throw new Error(
      "OIDC issuer requires HTTPS or an explicit loopback development issuer",
    );
  const manager = new UserManager({
    authority: issuer.href.replace(/\/$/, ""),
    client_id: config.client_id,
    redirect_uri: `${window.location.origin}/auth/callback`,
    response_type: "code",
    scope: "openid profile",
    userStore: new WebStorageStateStore({ store: new InMemoryWebStorage() }),
    stateStore: new WebStorageStateStore({
      store: window.sessionStorage,
      prefix: "mulenet.pkce.",
    }),
    automaticSilentRenew: false,
    loadUserInfo: false,
  });
  let user = null;
  if (window.location.pathname === "/auth/callback") {
    try {
      user = await manager.signinRedirectCallback();
    } finally {
      window.history.replaceState(null, "", "/");
    }
  }
  return { config, manager, user };
}
