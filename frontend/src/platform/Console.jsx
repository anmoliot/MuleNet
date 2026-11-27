import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  BrowserRouter,
  NavLink,
  Route,
  Routes,
  useNavigate,
  useParams,
} from "react-router-dom";
import {
  Activity,
  ArrowLeft,
  ArrowRight,
  Check,
  Download,
  FileClock,
  GitBranch,
  ListFilter,
  LogOut,
  Menu,
  RefreshCw,
  Settings2,
  ShieldAlert,
  X,
} from "lucide-react";
import { authentication } from "./auth.mjs";
import { createApi, dateTime, jsonValue, number, shortId } from "./client.mjs";

const EvidenceGraph = lazy(() => import("./EvidenceGraph.jsx"));
const has = (identity, ...roles) =>
  identity.roles.some((role) => roles.includes(role));
const Status = ({ value }) => (
  <span className={`status status-${value?.toLowerCase()}`}>
    {value?.replaceAll("_", " ") || "Unknown"}
  </span>
);
function IconButton({ label, children, ...props }) {
  return (
    <button
      type="button"
      className="icon-button"
      aria-label={label}
      title={label}
      {...props}
    >
      {children}
    </button>
  );
}
function ErrorNotice({ error, retry }) {
  return (
    <div className="error-notice" role="alert">
      <ShieldAlert size={18} />
      <span>{error?.message || String(error)}</span>
      {retry ? (
        <IconButton label="Retry request" onClick={retry}>
          <RefreshCw size={17} />
        </IconButton>
      ) : null}
    </div>
  );
}
function Loading() {
  return (
    <p className="loading" role="status">
      Loading authenticated data…
    </p>
  );
}
function useLoad(api, path, revision = 0) {
  const [state, setState] = useState(null);
  const key = `${path}:${revision}`;
  useEffect(() => {
    const controller = new AbortController();
    api
      .request(path, { signal: controller.signal })
      .then((data) => setState({ key, path, data }))
      .catch((error) => {
        if (!controller.signal.aborted) setState({ key, path, error });
      });
    return () => controller.abort();
  }, [api, path, key]);
  if (state?.key === key) return state;
  return state?.path === path && state.data
    ? { ...state, refreshing: true }
    : { loading: true };
}

export default function Console() {
  const [api] = useState(() => createApi());
  const [auth, setAuth] = useState(null);
  const [identity, setIdentity] = useState(null);
  const [error, setError] = useState(null);
  const [attempt, setAttempt] = useState(0);
  const accept = useCallback(
    async (token) => {
      api.setCredential(token);
      try {
        const session = await api.request("/auth/session");
        if (
          !session?.tenant ||
          !Array.isArray(session.roles) ||
          !Number.isFinite(session.expires_at)
        )
          throw new Error("Invalid authenticated session contract");
        setIdentity(session);
        setError(null);
      } catch (failure) {
        api.setCredential(null);
        throw failure;
      }
    },
    [api],
  );
  const logout = useCallback(() => {
    api.setCredential(null);
    setIdentity(null);
    auth?.manager?.removeUser().catch(() => {});
  }, [api, auth]);
  useEffect(() => {
    api.onUnauthorized(() => {
      auth?.manager?.removeUser().catch(() => {});
      setIdentity(null);
      setError(new Error("Session expired. Sign in again."));
    });
    return () => api.onUnauthorized(() => {});
  }, [api, auth]);
  useEffect(() => {
    let active = true;
    authentication(api)
      .then(async (value) => {
        if (!active) return;
        const token = value.user?.access_token;
        value.user = null;
        setAuth(value);
        if (token) await accept(token);
      })
      .catch((failure) => {
        if (active) setError(failure);
      });
    return () => {
      active = false;
    };
  }, [api, accept, attempt]);
  useEffect(() => {
    if (!identity) return;
    const timer = setTimeout(
      () => {
        logout();
        setError(new Error("Session expired. Sign in again."));
      },
      Math.max(0, identity.expires_at * 1000 - Date.now()),
    );
    return () => clearTimeout(timer);
  }, [identity, logout]);
  if (!identity)
    return (
      <Login
        auth={auth}
        error={error}
        retry={() => {
          setError(null);
          setAttempt((value) => value + 1);
        }}
        api={api}
        accept={accept}
      />
    );
  return (
    <BrowserRouter>
      <Workspace
        key={`${identity.tenant}:${identity.subject}`}
        api={api}
        identity={identity}
        logout={logout}
      />
    </BrowserRouter>
  );
}

function Login({ auth, error, retry, api, accept }) {
  const [pending, setPending] = useState(false);
  const [failure, setFailure] = useState(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  async function signIn(event) {
    event.preventDefault();
    setPending(true);
    setFailure(null);
    try {
      if (auth.manager) await auth.manager.signinRedirect();
      else {
        const result = await api.request("/auth/login", {
          method: "POST",
          body: { username, password },
        });
        if (!result?.access_token) throw new Error("Missing access token");
        await accept(result.access_token);
      }
    } catch (problem) {
      setFailure(problem);
    } finally {
      setPassword("");
      setPending(false);
    }
  }
  return (
    <main className="login-screen">
      <div className="login-brand">
        <GitBranch size={27} />
        <strong>MuleNet</strong>
        <span>Investigator console</span>
      </div>
      <section className="login-form" aria-labelledby="login-title">
        <p className="eyebrow">RESEARCH PLATFORM</p>
        <h1 id="login-title">Sign in</h1>
        <p className="muted">Not approved for production decisions.</p>
        {error || failure ? (
          <ErrorNotice error={failure || error} retry={!auth ? retry : null} />
        ) : null}
        {!auth ? (
          !error ? (
            <Loading />
          ) : null
        ) : (
          <form onSubmit={signIn}>
            {auth.config.mode === "demo" ? (
              <>
                <div className="notice">SIMULATED · Explicit demo profile</div>
                <label>
                  Username
                  <input
                    name="username"
                    autoComplete="username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    required
                    maxLength={64}
                  />
                </label>
                <label>
                  Password
                  <input
                    name="password"
                    type="password"
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    maxLength={256}
                  />
                </label>
              </>
            ) : (
              <p className="issuer">{new URL(auth.config.issuer).hostname}</p>
            )}
            <button className="primary" disabled={pending}>
              {pending
                ? "Signing in…"
                : auth.manager
                  ? "Continue with single sign-on"
                  : "Sign in"}
              <ArrowRight size={17} />
            </button>
          </form>
        )}
      </section>
    </main>
  );
}

function Workspace({ api, identity, logout }) {
  const [revision, setRevision] = useState(0);
  const [streamState, setStreamState] = useState("Connecting");
  const [streamAttempt, setStreamAttempt] = useState(0);
  const [mobileNav, setMobileNav] = useState(false);
  const refresh = useCallback(() => setRevision((value) => value + 1), []);
  useEffect(() => {
    const controller = new AbortController();
    let debounce;
    api
      .stream(controller.signal, setStreamState, () => {
        if (!debounce)
          debounce = setTimeout(() => {
            debounce = null;
            refresh();
          }, 200);
      })
      .catch(() => setStreamState("Disconnected"));
    return () => {
      controller.abort();
      clearTimeout(debounce);
    };
  }, [api, refresh, streamAttempt]);
  const navigation = [
    ["/", "Decisions", ListFilter],
    ["/health", "Health & drift", Activity],
    ...(has(identity, "SUPERVISOR", "ADMIN", "AUDITOR")
      ? [["/audit", "Audit trail", FileClock]]
      : []),
    ...(has(identity, "ADMIN")
      ? [["/policy", "Review policy", Settings2]]
      : []),
  ];
  return (
    <div className="workspace">
      <a className="skip-link" href="#workspace-main">
        Skip to content
      </a>
      <header className="workspace-top">
        <div className="console-brand">
          <IconButton
            label={mobileNav ? "Close navigation" : "Open navigation"}
            onClick={() => setMobileNav((value) => !value)}
          >
            <Menu size={20} />
          </IconButton>
          <GitBranch size={23} />
          <strong>MuleNet</strong>
          <span>Investigations</span>
        </div>
        <div className="session-meta">
          <span className="tenant" title={identity.tenant}>
            {identity.tenant}
          </span>
          <span>{identity.roles.join(", ")}</span>
          <IconButton label="Sign out" onClick={logout}>
            <LogOut size={18} />
          </IconButton>
        </div>
      </header>
      <aside className={mobileNav ? "workspace-nav is-open" : "workspace-nav"}>
        <nav aria-label="Investigator navigation">
          {navigation.map(([path, title, Icon]) => (
            <NavLink
              to={path}
              end={path === "/"}
              key={path}
              onClick={() => setMobileNav(false)}
            >
              <Icon size={18} />
              {title}
            </NavLink>
          ))}
        </nav>
        <div className="nav-foot">
          <span
            className={streamState === "Connected" ? "live-state" : "muted"}
          >
            {streamState}
          </span>
          <IconButton
            label="Reconnect decision stream"
            onClick={() => setStreamAttempt((value) => value + 1)}
          >
            <RefreshCw size={15} />
          </IconButton>
        </div>
      </aside>
      <main id="workspace-main" className="workspace-main">
        <div className="research-notice">
          <span>{identity.demo_mode ? "SIMULATED DEMO" : "RESEARCH ONLY"}</span>
          <span>Internal review states. No external bank intervention.</span>
        </div>
        <Routes>
          <Route
            path="/"
            element={<Queue api={api} revision={revision} refresh={refresh} />}
          />
          <Route
            path="/decisions/:id"
            element={
              <Case
                api={api}
                identity={identity}
                revision={revision}
                refresh={refresh}
              />
            }
          />
          <Route
            path="/health"
            element={<Health api={api} revision={revision} refresh={refresh} />}
          />
          <Route
            path="/policy"
            element={
              has(identity, "ADMIN") ? (
                <Policy api={api} revision={revision} refresh={refresh} />
              ) : (
                <p role="alert">Administrator role required.</p>
              )
            }
          />
          <Route
            path="/audit"
            element={
              has(identity, "SUPERVISOR", "ADMIN", "AUDITOR") ? (
                <Audit api={api} revision={revision} refresh={refresh} />
              ) : (
                <p role="alert">Your role cannot read the audit trail.</p>
              )
            }
          />
          <Route path="*" element={<p role="alert">Page not found.</p>} />
        </Routes>
      </main>
    </div>
  );
}

function PageHeading({ title, caption, refresh, children }) {
  return (
    <div className="page-heading">
      <div>
        <h1>{title}</h1>
        {caption ? <p>{caption}</p> : null}
      </div>
      <div className="heading-actions">
        {children}
        {refresh ? (
          <IconButton label="Reload records" onClick={refresh}>
            <RefreshCw size={18} />
          </IconButton>
        ) : null}
      </div>
    </div>
  );
}

function Queue({ api, revision, refresh }) {
  const query = useLoad(api, "/decisions", revision);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const navigate = useNavigate();
  const rows = useMemo(
    () =>
      query.data?.filter(
        (row) =>
          (!status || row.status === status) &&
          `${row.account_id} ${row.decision_id}`.includes(search.trim()),
      ) || [],
    [query.data, search, status],
  );
  return (
    <>
      <PageHeading
        title="Decision queue"
        caption="Latest tenant decisions · bounded to the API response, not a fleet-wide total"
        refresh={refresh}
      />
      <div className="queue-filters">
        <label>
          Account or decision token
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
        <label>
          Review state
          <select
            aria-label="Review state"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            <option value="">All states</option>
            {[
              "SOFT_HOLD",
              "UNDER_REVIEW",
              "HOLD_APPROVED",
              "MONITOR",
              "RELEASED",
              "REJECTED",
            ].map((value) => (
              <option key={value}>{value}</option>
            ))}
          </select>
        </label>
        {query.data ? (
          <span className="meta">
            {rows.length} shown / {query.data.length} loaded
          </span>
        ) : null}
      </div>
      {query.loading ? (
        <Loading />
      ) : query.error ? (
        <ErrorNotice error={query.error} retry={refresh} />
      ) : !rows.length ? (
        <p className="empty-state">No decisions match this view.</p>
      ) : (
        <div className="table-scroll">
          <table className="decision-table">
            <thead>
              <tr>
                <th>Account</th>
                <th>Review state</th>
                <th>Model probability</th>
                <th>Model</th>
                <th>As of</th>
                <th>Provenance</th>
                <th>
                  <span className="sr-only">Open</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.decision_id}>
                  <td>
                    <span className="mono" title={row.account_id}>
                      {shortId(row.account_id)}
                    </span>
                    <small title={row.decision_id}>
                      {shortId(row.decision_id)}
                    </small>
                  </td>
                  <td>
                    <Status value={row.status} />
                  </td>
                  <td className="numeric">{number(row.result.probability)}</td>
                  <td>
                    <span>{row.result.model}</span>
                    {row.result.degraded ? (
                      <small className="degraded-text">DEGRADED</small>
                    ) : (
                      <small title={row.result.model_version}>
                        {shortId(row.result.model_version)}
                      </small>
                    )}
                  </td>
                  <td>{dateTime(row.as_of)}</td>
                  <td>
                    <span className="simulated">
                      {row.result.data_provenance?.toUpperCase() ||
                        "NOT RECORDED"}
                    </span>
                  </td>
                  <td>
                    <IconButton
                      label={`Open decision ${row.decision_id}`}
                      onClick={() => navigate(`/decisions/${row.decision_id}`)}
                    >
                      <ArrowRight size={18} />
                    </IconButton>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function Case({ api, identity, revision, refresh }) {
  const { id } = useParams();
  const query = useLoad(api, `/decisions/${encodeURIComponent(id)}`, revision);
  const notes = useLoad(
    api,
    `/decisions/${encodeURIComponent(id)}/notes`,
    revision,
  );
  const navigate = useNavigate();
  return (
    <>
      <PageHeading title="Decision review" refresh={refresh}>
        <IconButton
          label="Back to decision queue"
          onClick={() => navigate("/")}
        >
          <ArrowLeft size={18} />
        </IconButton>
      </PageHeading>
      {query.loading ? (
        <Loading />
      ) : query.error ? (
        <ErrorNotice error={query.error} retry={refresh} />
      ) : (
        <CaseRecord
          key={id}
          decision={query.data}
          api={api}
          identity={identity}
          refresh={refresh}
          notes={notes}
        />
      )}
    </>
  );
}

function CaseRecord({ decision, api, identity, refresh, notes }) {
  const [timeline, setTimeline] = useState(null);
  const [action, setAction] = useState("NOTE");
  const [rationale, setRationale] = useState("");
  const [assignee, setAssignee] = useState("");
  const [error, setError] = useState(null);
  const [pending, setPending] = useState(false);
  const [success, setSuccess] = useState("");
  const times = [
    ...new Set([
      ...decision.result.evidence.edges.map((edge) => edge.ts),
      Number(decision.as_of),
    ]),
  ].sort((a, b) => a - b);
  const timeIndex =
    timeline === null ? times.length - 1 : Math.min(timeline, times.length - 1);
  const canWrite = has(identity, "ANALYST", "SUPERVISOR", "ADMIN");
  const privileged = has(identity, "SUPERVISOR", "ADMIN");
  const actions = [
    "NOTE",
    "APPEAL",
    ...(privileged ? ["ASSIGN", "APPROVE", "REJECT", "RELEASE"] : []),
  ];
  async function submit(event) {
    event.preventDefault();
    setPending(true);
    setError(null);
    setSuccess("");
    const suffix =
      action === "NOTE"
        ? "notes"
        : action === "APPEAL"
          ? "appeal"
          : `actions/${action}`;
    try {
      await api.request(`/decisions/${decision.decision_id}/${suffix}`, {
        method: "POST",
        body: {
          expectedVersion: decision.version,
          rationale,
          ...(action === "ASSIGN" ? { assignee } : {}),
        },
      });
      setRationale("");
      setAction("NOTE");
      setSuccess("Review recorded.");
      refresh();
    } catch (failure) {
      setError(failure);
    } finally {
      setPending(false);
    }
  }
  async function draft() {
    setError(null);
    try {
      const value = await api.request(
        `/decisions/${decision.decision_id}/str-draft`,
      );
      const href = URL.createObjectURL(
        new Blob([JSON.stringify(value, null, 2)], {
          type: "application/json",
        }),
      );
      const link = document.createElement("a");
      link.href = href;
      link.download = "mulenet-str-draft-template.json";
      link.click();
      setTimeout(() => URL.revokeObjectURL(href), 1000);
    } catch (failure) {
      setError(failure);
    }
  }
  const result = decision.result;
  return (
    <>
      <div className="case-summary">
        <div>
          <p className="eyebrow">ACCOUNT TOKEN</p>
          <p className="token-value">{decision.account_id}</p>
          <p className="meta">Decision {decision.decision_id}</p>
        </div>
        <Status value={decision.status} />
      </div>
      {result.degraded ? (
        <div className="degraded-banner" role="status">
          <ShieldAlert size={18} />
          <strong>DEGRADED · {result.degradation_reason}</strong>
          <span>No substitute model probability.</span>
        </div>
      ) : null}
      <div className="decision-facts">
        {[
          ["Model probability", number(result.probability)],
          ["Policy threshold", number(result.policy_threshold)],
          ["Expires", dateTime(decision.expires_at)],
          ["Record version", decision.version],
        ].map(([label, value]) => (
          <div key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
      <div className="case-columns">
        <section className="case-evidence">
          <h2>Observed evidence</h2>
          <label className="timeline-label">
            Evidence through {dateTime(times[timeIndex])}
            <input
              aria-label="Evidence time"
              type="range"
              min="0"
              max={times.length - 1}
              value={timeIndex}
              disabled={times.length < 2}
              onChange={(event) => setTimeline(Number(event.target.value))}
            />
          </label>
          <Suspense fallback={<Loading />}>
            <EvidenceGraph decision={decision} cutoff={times[timeIndex]} />
          </Suspense>
          <div className="record-identities">
            <p>
              Model version <code>{result.model_version}</code>
            </p>
            <p>
              Feature schema{" "}
              <code>{result.feature_schema_hash || "Unavailable"}</code>
            </p>
            <p>
              Policy version <code>{result.thresholds_version}</code>
            </p>
            <p>
              Data provenance <strong>{result.data_provenance}</strong>
            </p>
          </div>
          <h2>Reason codes</h2>
          {result.reason_codes.map((reason, index) => (
            <details
              className="reason-code"
              key={`${reason.code}-${index}`}
              open
            >
              <summary>{reason.code}</summary>
              {reason.features ? (
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Feature</th>
                        <th>Value</th>
                        <th>SHAP log-odds</th>
                      </tr>
                    </thead>
                    <tbody>
                      {reason.features.map((feature) => (
                        <tr key={feature.feature}>
                          <td>{feature.feature}</td>
                          <td className="numeric">{number(feature.value)}</td>
                          <td className="numeric">
                            {number(feature.shap_log_odds)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <pre>{JSON.stringify(reason, null, 2)}</pre>
              )}
            </details>
          ))}
          <h2>Score components</h2>
          <dl className="score-components">
            {Object.entries(result.score_components || {}).map(
              ([name, value]) => (
                <div key={name}>
                  <dt>
                    {name === "anomaly_signal"
                      ? "anomaly_signal (unsupervised)"
                      : name}
                  </dt>
                  <dd>
                    {typeof value === "boolean" ? String(value) : number(value)}
                  </dd>
                </div>
              ),
            )}
          </dl>
        </section>
        <section className="case-review">
          <h2>Case review</h2>
          <dl className="review-metadata">
            <div>
              <dt>Assignee token</dt>
              <dd title={decision.assignee}>{shortId(decision.assignee)}</dd>
            </div>
            <div>
              <dt>External intervention</dt>
              <dd>
                {result.external_intervention === false
                  ? "None"
                  : result.external_intervention === true
                    ? "Recorded external intervention"
                    : "Not recorded"}
              </dd>
            </div>
          </dl>
          {error ? <ErrorNotice error={error} /> : null}
          {success ? (
            <p role="status" className="success-text">
              <Check size={16} />
              {success}
            </p>
          ) : null}
          {canWrite ? (
            <form className="review-form" onSubmit={submit}>
              <label>
                Action
                <select
                  aria-label="Action"
                  value={action}
                  onChange={(event) => setAction(event.target.value)}
                >
                  {actions.map((value) => (
                    <option key={value}>{value}</option>
                  ))}
                </select>
              </label>
              {action === "ASSIGN" ? (
                <label>
                  Assignee identifier
                  <input
                    value={assignee}
                    onChange={(event) => setAssignee(event.target.value)}
                    pattern="[a-zA-Z0-9_-]+"
                    maxLength={128}
                    required
                  />
                </label>
              ) : null}
              <label>
                Rationale
                <textarea
                  minLength={10}
                  maxLength={2000}
                  required
                  value={rationale}
                  onChange={(event) => setRationale(event.target.value)}
                />
              </label>
              <button className="primary" disabled={pending}>
                {pending ? "Recording…" : "Record review"}
                <Check size={16} />
              </button>
            </form>
          ) : (
            <p className="meta">Read-only auditor session.</p>
          )}
          {has(identity, "SUPERVISOR", "ADMIN", "AUDITOR") ? (
            <button
              className="secondary draft-button"
              type="button"
              onClick={draft}
            >
              <Download size={16} />
              STR draft template
            </button>
          ) : null}
          <h2>Notes and actions</h2>
          {notes.loading ? (
            <Loading />
          ) : notes.error ? (
            <ErrorNotice error={notes.error} retry={refresh} />
          ) : !notes.data?.length ? (
            <p className="meta">No review notes recorded.</p>
          ) : (
            <ol className="case-history">
              {notes.data.map((note, i) => (
                <li key={`${note.time}-${i}`}>
                  <strong>{note.action.replace("CASE_", "")}</strong>
                  <span>{dateTime(note.time)}</span>
                  <p>{note.rationale}</p>
                  <small title={note.actor}>{shortId(note.actor)}</small>
                </li>
              ))}
            </ol>
          )}
        </section>
      </div>
    </>
  );
}

function Policy({ api, revision, refresh }) {
  const query = useLoad(api, "/policy", revision);
  return (
    <>
      <PageHeading
        title="Review policy"
        caption="Versioned, change-audited internal review policy"
        refresh={refresh}
      />
      {query.loading ? (
        <Loading />
      ) : query.error ? (
        <ErrorNotice error={query.error} retry={refresh} />
      ) : (
        <PolicyEditor
          key={query.data.version}
          api={api}
          row={query.data}
          refresh={refresh}
        />
      )}
    </>
  );
}
function PolicyEditor({ api, row, refresh }) {
  const config = jsonValue(row.config);
  const [automatic, setAutomatic] = useState(config.reviewThreshold === null);
  const [error, setError] = useState(null);
  const [pending, setPending] = useState(false);
  async function save(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setPending(true);
    setError(null);
    try {
      await api.request("/policy", {
        method: "PUT",
        body: {
          expectedVersion: row.version,
          rationale: form.get("rationale"),
          config: {
            maxHoldSeconds: Number(form.get("maxHoldSeconds")),
            reviewThreshold: automatic
              ? null
              : Number(form.get("reviewThreshold")),
            falseFreezeCostInr: Number(form.get("falseFreezeCostInr")),
            missedRiskCostInr: Number(form.get("missedRiskCostInr")),
          },
        },
      });
      refresh();
    } catch (failure) {
      setError(failure);
    } finally {
      setPending(false);
    }
  }
  return (
    <form className="policy-form" onSubmit={save}>
      <p className="meta">
        Current version {row.version}. Costs below are assumptions, not measured
        financial losses.
      </p>
      {error ? <ErrorNotice error={error} /> : null}
      <div className="form-grid">
        <label>
          Maximum hold duration (seconds)
          <input
            name="maxHoldSeconds"
            type="number"
            min="1"
            max="86400"
            step="1"
            defaultValue={config.maxHoldSeconds}
            required
          />
        </label>
        <label>
          False-freeze cost assumption (INR)
          <input
            name="falseFreezeCostInr"
            type="number"
            min="0.01"
            max="1000000000000"
            step="any"
            defaultValue={config.falseFreezeCostInr}
            required
          />
        </label>
        <label>
          Missed-risk cost assumption (INR)
          <input
            name="missedRiskCostInr"
            type="number"
            min="0.01"
            max="1000000000000"
            step="any"
            defaultValue={config.missedRiskCostInr}
            required
          />
        </label>
        <div>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={automatic}
              onChange={(event) => setAutomatic(event.target.checked)}
            />
            Use validation-selected threshold
          </label>
          {!automatic ? (
            <label>
              Review threshold
              <input
                name="reviewThreshold"
                type="number"
                min="0"
                max="1"
                step="any"
                defaultValue={config.reviewThreshold ?? ""}
                required
              />
            </label>
          ) : null}
        </div>
      </div>
      <label>
        Change rationale
        <textarea name="rationale" minLength={10} maxLength={2000} required />
      </label>
      <button className="primary" disabled={pending}>
        {pending ? "Saving…" : "Save policy version"}
        <Check size={16} />
      </button>
    </form>
  );
}

function Audit({ api, revision, refresh }) {
  const [cursors, setCursors] = useState([0]);
  const query = useLoad(
    api,
    `/audit?after=${cursors.at(-1)}&limit=50`,
    revision,
  );
  return (
    <>
      <PageHeading
        title="Audit trail"
        caption="Append-only, tenant-scoped recorded actions"
        refresh={refresh}
      />
      {query.loading ? (
        <Loading />
      ) : query.error ? (
        <ErrorNotice error={query.error} retry={refresh} />
      ) : (
        <>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Sequence</th>
                  <th>Time</th>
                  <th>Action</th>
                  <th>Actor token</th>
                  <th>Entry hash</th>
                </tr>
              </thead>
              <tbody>
                {query.data.map((row) => {
                  const payload = jsonValue(row.payload);
                  return (
                    <tr key={row.sequence}>
                      <td className="numeric">{row.sequence}</td>
                      <td>{dateTime(payload.time)}</td>
                      <td>{payload.action}</td>
                      <td title={payload.actor}>{shortId(payload.actor)}</td>
                      <td title={row.entry_hash}>
                        <code>{shortId(row.entry_hash)}</code>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {!query.data.length ? (
            <p className="empty-state">No audit entries on this page.</p>
          ) : null}
          <div className="pagination">
            <IconButton
              label="Previous audit page"
              disabled={cursors.length === 1}
              onClick={() => setCursors((value) => value.slice(0, -1))}
            >
              <ArrowLeft size={18} />
            </IconButton>
            <span>{query.data.length} entries loaded</span>
            <IconButton
              label="Next audit page"
              disabled={query.data.length < 50}
              onClick={() =>
                setCursors((value) => [...value, query.data.at(-1).sequence])
              }
            >
              <ArrowRight size={18} />
            </IconButton>
          </div>
        </>
      )}
    </>
  );
}

function Health({ api, revision, refresh }) {
  const health = useLoad(api, "/health", revision);
  const drift = useLoad(api, "/drift", revision);
  return (
    <>
      <PageHeading
        title="Health & drift"
        caption="Tenant-scoped service state; not a production-readiness certification"
        refresh={refresh}
      />
      <section className="health-state">
        <h2>Service boundary</h2>
        {health.loading ? (
          <Loading />
        ) : health.error ? (
          <ErrorNotice error={health.error} retry={refresh} />
        ) : (
          <dl className="score-components">
            <div>
              <dt>ML scoring circuit</dt>
              <dd>{health.data.ml_circuit}</dd>
            </div>
            <div>
              <dt>Tenant</dt>
              <dd>{health.data.tenant}</dd>
            </div>
            <div>
              <dt>Production approved</dt>
              <dd>{String(health.data.production_approved)}</dd>
            </div>
          </dl>
        )}
      </section>
      <section className="drift-state">
        <h2>Observed feature and score drift</h2>
        <p className="meta">
          Data review signals only. No automatic promotion, retraining or
          financial hold.
        </p>
        {drift.loading ? (
          <Loading />
        ) : drift.error ? (
          <ErrorNotice error={drift.error} retry={refresh} />
        ) : !drift.data.windows?.length ? (
          <p className="empty-state">
            No tenant drift observations available. Readiness is unknown, not
            healthy.
          </p>
        ) : (
          drift.data.windows.map((window) => (
            <details
              className="drift-window"
              key={`${window.model_version}:${window.model}:${window.reference_sha256}`}
            >
              <summary>
                <span>
                  {window.model} · {shortId(window.model_version)}
                </span>
                <span>
                  {window.samples} observations ·{" "}
                  {window.ready
                    ? window.review_required
                      ? "Data review requested"
                      : "No review trigger"
                    : "Insufficient observations"}
                </span>
              </summary>
              <p className="meta">
                Training reference {window.reference_sha256}
              </p>
              {window.ready && window.statistics ? (
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Feature / score</th>
                        <th>PSI</th>
                        <th>KS</th>
                        <th>KS p-value</th>
                        <th>Review trigger</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(window.statistics).map(
                        ([name, value]) => (
                          <tr key={name}>
                            <td>{name}</td>
                            <td className="numeric">{number(value.psi)}</td>
                            <td className="numeric">{number(value.ks)}</td>
                            <td className="numeric">
                              {number(value.ks_pvalue)}
                            </td>
                            <td>{String(value.review_trigger)}</td>
                          </tr>
                        ),
                      )}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="meta">
                  No PSI/KS verdict is available for this window.
                </p>
              )}
            </details>
          ))
        )}
      </section>
    </>
  );
}
