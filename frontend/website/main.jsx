import { StrictMode, useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  ArrowDown, ArrowRight, ArrowUpRight, Check, ChevronDown, Code2, Database,
  FileCheck2, FileText, GitBranch, CodeXml, Layers3, Maximize2, Menu,
  Network, Radio, SearchCheck, ShieldCheck, Terminal, X,
} from 'lucide-react';
import '@fontsource/ibm-plex-sans/latin-400.css';
import '@fontsource/ibm-plex-sans/latin-500.css';
import '@fontsource/ibm-plex-sans/latin-600.css';
import '@fontsource/ibm-plex-mono/latin-400.css';
import '@fontsource/ibm-plex-mono/latin-500.css';
import './site.css';

const REPO = 'https://github.com/anmoliot/MuleNet';
const graphDescription = 'Illustrative transfer network: A001 sends to A014, which branches into two paths. The upper path passes through A027, A033 and A042 to A058. Coral edges mark a relay pattern for review, not proof of fraud. The lower path ends at the reviewed account A031.';
const faq = [
  ['What is MuleNet, exactly?', 'An open-source research platform for evaluating graph-based money-mule detection and investigator review. It combines a streaming backend, shared as-of features, model evaluation and auditable decisions. It is not a production fraud-prevention service.'],
  ['Are the results from real bank transactions?', 'No. The published evidence comes from simulated datasets, including PaySim and a local typology generator. PaySim evaluates contemporaneous transaction classification, not future account or ring detection. No recovery or real-world financial benefit has been measured.'],
  ['Does it connect directly to I4C or NCRP?', 'No. The watchlist provider is a simulated I4C/NCRP-style adapter. MuleNet has no direct access to those systems and makes no claim of an official partnership or regulatory approval.'],
  ['Does a suspicious score automatically freeze an account?', 'No bank account is frozen by this project. SOFT_HOLD is a time-limited internal review state with release and review paths. A score is a signal to investigate, not a finding of guilt.'],
  ['Can I deploy this in production?', 'Not as a production decision system. Security acceptance has failed on documented unresolved findings, the legacy investigator UI needs API migration, and full deployment-scale acceptance is unfinished. This public website exposes none of the scoring, ingestion or case-management endpoints.'],
  ['Can I run or contribute to the research?', 'Yes. Start with the repository README, data-license notes and contribution guide. Dataset access is separate from the code license. Synthetic runs require an explicit opt-in, and generated reports must retain their provenance and limitations.'],
];
const setupPlans = [
  { name: 'Explore', tag: 'Start here', value: 'Open source', caption: 'Read before you run.', icon: Code2, action: 'Browse repository', href: REPO, items: ['Source and architecture', 'Recorded evaluation evidence', 'Known limitations', 'No account required'] },
  { name: 'Reproduce', tag: 'Recommended for research', value: 'Self-hosted', caption: 'Your environment. Your checks.', icon: Terminal, action: 'View local setup', modal: 'start', items: ['Pinned project dependencies', 'Explicit synthetic-data opt-in', 'Temporal and entity splits', 'Generated reports and tests'], recommended: true },
  { name: 'Production', tag: 'Not offered', value: 'Not ready', caption: 'No implied readiness.', icon: ShieldCheck, action: 'Read the limitations', href: '#questions', items: ['Security findings remain open', 'No managed hosting or SLA', 'No real bank validation', 'Not for production decisions'] },
];

function Mark({ small = false }) {
  return <span className={`wordmark${small ? ' wordmark-small' : ''}`}><GitBranch aria-hidden="true" /><span>MuleNet</span></span>;
}
function Action({ children, href, onClick, secondary = false, className = '', ...props }) {
  const cls = `action ${secondary ? 'action-secondary' : 'action-primary'} ${className}`;
  return href ? <a className={cls} href={href} {...props}>{children}</a> : <button className={cls} onClick={onClick} type="button" {...props}>{children}</button>;
}
function SectionHeading({ id, first, second, href, label, onClick }) {
  return <div className="section-heading"><h2 id={id}>{first}<br />{second}</h2>{href ? <a className="icon-link" href={href} aria-label={label} title={label}><ArrowUpRight aria-hidden="true" /></a> : <button className="icon-link" type="button" onClick={onClick} aria-label={label} title={label}><ArrowUpRight aria-hidden="true" /></button>}</div>;
}
function Metric({ name, metric, percent = false, full = false }) {
  const format = value => percent ? `${(value * 100).toFixed(2)}%` : value.toFixed(4);
  return <div className="metric"><strong>{format(metric.value)}</strong><span>{name}</span>{full ? <small>95% CI {format(metric.ci95[0])}–{format(metric.ci95[1])}</small> : null}</div>;
}
function Metrics({ record, full = false }) {
  return <div className="metrics"><Metric name="PR-AUC" metric={record.pr_auc} full={full} /><Metric name="Recall" metric={record.recall} percent full={full} /><Metric name="False-positive rate" metric={record.fpr} percent full={full} /></div>;
}
function AsOfTimeline() {
  const [cutoff, setCutoff] = useState(1);
  const events = ['Receipt observed', 'As-of decision', 'Later onward transfer'];
  return <div className="timeline-tool"><div className="tool-caption"><span>FEATURE BOUNDARY</span><span>ILLUSTRATIVE</span></div><div className="time-axis">{events.map((label, i) => <div className={`time-event ${i > cutoff ? 'is-future' : ''}`} key={label}><span className="event-dot" /><strong>{label}</strong><small>{i > cutoff ? 'Excluded: future event' : 'Available at this point'}</small></div>)}</div><label className="range-label" htmlFor="asof">As-of point <span>{events[cutoff]}</span></label><input id="asof" aria-label="As-of point" type="range" min="0" max="2" step="1" value={cutoff} onChange={event => setCutoff(Number(event.target.value))} /><p className="tool-note">Only observations at or before the selected point belong in its features.</p></div>;
}
function DecisionRecord() {
  return <div className="decision-tool"><div className="tool-caption"><span>DECISION RECORD</span><span>ILLUSTRATIVE</span></div><div className="decision-state"><FileCheck2 aria-hidden="true" /><div><strong>Keep the reason.</strong><span>Not just the score.</span></div></div><dl>{[['Model identity', 'Verified artifact'], ['Feature boundary', 'As-of snapshot'], ['Policy identity', 'Versioned thresholds'], ['Review outcome', 'Human decision']].map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value}<Check size={14} aria-hidden="true" /></dd></div>)}</dl><div className="audit-chain"><span>Observation</span><ArrowRight size={14} /><span>Decision</span><ArrowRight size={14} /><span>Audit trail</span></div></div>;
}
function EvidencePanel({ evidence, error, retry }) {
  const [dataset, setDataset] = useState('paysim');
  return <div className="evidence-tool"><div className="tool-caption"><span>RECORDED EVALUATION</span><span>SIMULATED DATA</span></div><div className="segmented" aria-label="Evaluation dataset">{[['paysim', 'PaySim'], ['simulator', 'Account simulator']].map(([key, title]) => <button type="button" key={key} aria-pressed={dataset === key} onClick={() => setDataset(key)}>{title}</button>)}</div>{!evidence ? <div className="data-state" role="status">{error ? <><p>Evidence could not be loaded. No substitute figures are shown.</p><button className="text-link" onClick={retry} type="button">Retry loading <ArrowRight size={16} /></button></> : 'Loading recorded evidence…'}</div> : dataset === 'paysim' ? <><p className="evidence-title">Pre-transfer XGBoost · temporal test</p><Metrics record={evidence.paysim} full /><p className="tool-note">Transaction classification, not topology validation. Row-bootstrap intervals do not model account dependence.</p></> : <><p className="evidence-title">XGBoost + graph features</p><div className="split-results">{evidence.simulator.map(record => <div key={record.split}><span>{record.split}</span><strong>{(record.recall.value * 100).toFixed(2)}%</strong><small>test recall at the selected operating point</small></div>)}</div><p className="tool-note">No test recall at this strict validation-selected operating point. A useful limitation, not a result to hide.</p></>}<a className="text-link evidence-source" href="/evidence.json" download="mulenet-evidence.json">Download source evidence <ArrowDown size={16} aria-hidden="true" /></a></div>;
}
function Site() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [modal, setModal] = useState(null);
  const [evidence, setEvidence] = useState(null);
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);
  const [reviewStep, setReviewStep] = useState(0);
  const dialog = useRef(null);
  useEffect(() => {
    const controller = new AbortController();
    fetch('/evidence.json', { signal: controller.signal }).then(response => {
      if (!response.ok) throw new Error('Evidence unavailable');
      return response.json();
    }).then(value => {
      if (value.data_provenance !== 'synthetic' || !value.paysim?.pr_auc || !Array.isArray(value.simulator)) throw new Error('Unexpected evidence schema');
      setEvidence(value);
      setError(false);
    }).catch(failure => { if (failure.name !== 'AbortError') setError(true); });
    return () => controller.abort();
  }, [retry]);
  useEffect(() => {
    if (modal && !dialog.current.open) dialog.current.showModal();
    if (!modal && dialog.current.open) dialog.current.close();
  }, [modal]);
  useEffect(() => {
    if (!menuOpen) return;
    const close = event => { if (event.key === 'Escape') setMenuOpen(false); };
    document.addEventListener('keydown', close);
    return () => document.removeEventListener('keydown', close);
  }, [menuOpen]);
  const openModal = name => { setMenuOpen(false); setModal(name); };
  const reload = () => { setError(false); setRetry(value => value + 1); };
  return <>
    <a className="skip-link" href="#main">Skip to content</a>
    <div className="announcement"><span>OPEN-SOURCE RESEARCH</span><span className="announcement-extra"> / SIMULATED BENCHMARKS / HUMAN REVIEW</span></div>
    <header className="site-header wrap">
      <a className="brand-link" href="#" aria-label="MuleNet home"><Mark /></a>
      <nav className={menuOpen ? 'navigation is-open' : 'navigation'} id="site-navigation" aria-label="Main navigation">{[['Product', '#product'], ['Evidence', '#evidence'], ['Workflow', '#workflow'], ['Docs', `${REPO}#readme`]].map(([title, href]) => <a href={href} key={title} onClick={() => setMenuOpen(false)}>{title}</a>)}</nav>
      <div className="header-actions"><a className="github-link" href={REPO} aria-label="MuleNet on GitHub" title="MuleNet on GitHub"><CodeXml /></a><Action onClick={() => openModal('start')}>Explore project <ArrowRight size={18} /></Action><button type="button" className="menu-toggle" aria-controls="site-navigation" aria-expanded={menuOpen} aria-label={menuOpen ? 'Close navigation' : 'Open navigation'} onClick={() => setMenuOpen(value => !value)}>{menuOpen ? <X /> : <Menu />}</button></div>
    </header>
    <main id="main">
      <section className="hero" aria-labelledby="hero-title">
        <div className="hero-scene wrap">
          <div className="hero-copy"><h1 id="hero-title">MuleNet</h1><p className="hero-tagline">Follow the evidence.</p><p className="hero-description">Graph-based money-mule detection. Reproducible research. Human review.</p><div className="hero-actions"><Action onClick={() => openModal('start')}>Explore the project <ArrowRight size={18} /></Action><Action href="#evidence" secondary><FileText size={17} />Read the evidence</Action></div><p className="trust-caption">Research software. Simulated data.<br />Not for production decisions.</p><div className="hero-proof"><p className="eyebrow">Recorded PaySim temporal test / simulated</p>{evidence ? <><Metrics record={evidence.paysim} /><p className="metric-footnote">PR-AUC 95% CI: {evidence.paysim.pr_auc.ci95.map(value => value.toFixed(4)).join('–')}.<br />Transaction classification, not topology validation.</p></> : <p className="metric-footnote" role="status">{error ? 'Evidence unavailable. No substitute metrics.' : 'Loading recorded evidence…'}</p>}</div></div>
          <figure className="hero-graph"><div className="graph-toolbar"><span>Evidence explorer</span><span className="sample-badge">ILLUSTRATIVE / SIMULATED</span><button className="icon-link" type="button" aria-label="Expand illustrative evidence graph" title="Expand illustrative evidence graph" onClick={() => openModal('graph')}><Maximize2 size={17} /></button></div><div className="graph-picture"><p className="path-label">Relay pattern / needs review</p><img src="/evidence-graph-alpha.png" width="1737" height="905" alt={graphDescription} fetchPriority="high" /></div><figcaption><div className="graph-legend"><span><i className="legend-node" />Account</span><span><i className="legend-edge" />Transfer</span><span><i className="legend-edge legend-alert" />Review path</span></div><button className="review-summary" onClick={() => openModal('graph')} type="button"><span><strong>Account A042</strong><span className="hold-label">SOFT_HOLD</span></span><span>Review required <ArrowUpRight size={16} /></span></button></figcaption></figure>
        </div>
      </section>
      <section className="foundations wrap" aria-labelledby="foundations-title"><SectionHeading id="foundations-title" first="Built on open" second="foundations." href={`${REPO}#architecture`} label="View the project architecture" /><p className="section-caption">Technology stack, not customer endorsements.</p><div className="stack-marks">{[[Layers3, 'Spring Boot'], [Code2, 'FastAPI'], [GitBranch, 'React'], [Radio, 'Kafka'], [Database, 'PostgreSQL'], [Network, 'Redis']].map(([Icon, name]) => <span key={name}><Icon aria-hidden="true" /><span>{name}</span></span>)}</div></section>
      <section className="features band alternate" id="product" aria-labelledby="features-title"><div className="wrap"><SectionHeading id="features-title" first="Less black box." second="More evidence." href={`${REPO}#architecture`} label="Explore the architecture" /><div className="feature-row"><div className="feature-visual graph-feature"><div className="tool-caption"><span>CONNECTED ACCOUNTS</span><span>ILLUSTRATIVE</span></div><img src="/evidence-graph-alpha.png" width="1737" height="905" alt={graphDescription} loading="lazy" /><div className="feature-graph-caption"><span className="tiny-dot" />A pattern to investigate. Not a verdict.</div></div><div className="feature-copy"><span className="eyebrow">Context, not isolated transactions</span><h3>Follow the path.<br />Keep the context.</h3><p>Money moves through relationships. Explore incoming and onward flows, connected accounts and the evidence behind a review signal.</p><p className="copy-note">The watchlist adapter is simulated. A highlighted path is never proof of wrongdoing.</p></div></div><div className="feature-row feature-reverse"><AsOfTimeline /><div className="feature-copy"><span className="eyebrow">A boundary that matters</span><h3>Only what was<br />known at the time.</h3><p>Training and serving share as-of feature code. Later transactions belong in the future label window, not in the features that predict it.</p><p className="copy-note">Future transactions cannot explain an earlier decision.</p></div></div><div className="feature-row evidence-row" id="evidence"><EvidencePanel evidence={evidence} error={error} retry={reload} /><div className="feature-copy"><span className="eyebrow">Evidence over promises</span><h3>The result includes<br />the limitations.</h3><p>Read the operating point, dataset and uncertainty together. A simulated transaction benchmark cannot establish real-world ring detection.</p><p className="copy-note">The account simulator recorded no test recall at its selected strict operating point. The GNN did not earn the default path.</p></div></div></div></section>
      <section className="workflow band" id="workflow" aria-labelledby="workflow-title"><div className="wrap"><SectionHeading id="workflow-title" first="Observe clearly." second="Decide responsibly." onClick={() => openModal('start')} label="View the local research setup" /><div className="workflow-layout"><div><p className="workflow-intro">A research workflow with an evidence trail.<br /><span>No claim of a live bank integration.</span></p><DecisionRecord /></div><ol className="process-steps">{[['Observe', 'Ingest account-keyed events. Build bounded, time-aware features without looking into the future.', Network], ['Evaluate', 'Compare verified candidates and record the selected model, feature schema and policy version.', SearchCheck], ['Review', 'Keep reason codes and an audit trail. Give investigators a defined review and release path.', FileCheck2]].map(([title, body, Icon], i) => <li key={title}><span className="step-number">{String(i + 1).padStart(2, '0')}</span><div><h3>{title}<Icon size={20} aria-hidden="true" /></h3><p>{body}</p></div></li>)}</ol></div></div></section>
      <section className="principles band alternate" aria-labelledby="principles-title"><div className="wrap"><SectionHeading id="principles-title" first="Trust is a practice." second="Not a testimonial." href={`${REPO}#current-status`} label="Read the current project status" /><p className="section-caption">Project principles, not customer endorsements.</p><blockquote className="main-quote"><span className="quote-mark" aria-hidden="true">“</span><p>A suspicious pattern is a reason to investigate. Not a reason to skip the evidence.</p><footer><span className="initial-avatar" aria-hidden="true"><SearchCheck /></span><span>MuleNet research principle<small>Human review and false-freeze harm</small></span></footer></blockquote><div className="supporting-quotes"><blockquote><p>Report what the experiment measured. Keep what it didn’t measure just as visible.</p><footer><span className="initial-avatar" aria-hidden="true"><FileText /></span><span>Honest evaluation<small>Dataset, operating point, uncertainty</small></span></footer></blockquote><blockquote><p>A reproducible weak result is more useful than an unsupported strong claim.</p><footer><span className="initial-avatar" aria-hidden="true"><GitBranch /></span><span>Reproducible research<small>Generated reports, shared feature code</small></span></footer></blockquote></div></div></section>
      <section className="setups band" id="setups" aria-labelledby="setups-title"><div className="wrap"><SectionHeading id="setups-title" first="Choose your" second="starting point." href={`${REPO}/blob/main/LICENSE`} label="Read the source code license" /><p className="section-caption">Research setups, not commercial subscription plans. Infrastructure and data access are separate.</p><div className="setup-grid">{setupPlans.map(plan => <article className={`setup-plan${plan.recommended ? ' recommended' : ''}`} key={plan.name}><div className="plan-top"><plan.icon size={22} aria-hidden="true" /><span>{plan.tag}</span></div><h3>{plan.name}</h3><p className="plan-value">{plan.value}</p><p>{plan.caption}</p><Action href={plan.href} onClick={plan.modal ? () => openModal(plan.modal) : undefined} secondary={!plan.recommended}>{plan.action}<ArrowUpRight size={16} /></Action><ul>{plan.items.map(item => <li key={item}><Check size={16} aria-hidden="true" />{item}</li>)}</ul></article>)}</div><p className="setups-note">Source code is MIT-licensed. This is not a managed service, a production offer or a promise of support.</p></div></section>
      <section className="faq band alternate" id="questions" aria-labelledby="faq-title"><div className="wrap"><SectionHeading id="faq-title" first="Good questions." second="Straight answers." href={`${REPO}/issues`} label="Ask a question on GitHub" /><div className="faq-layout"><p className="faq-intro">The boundaries are part<br />of the product.</p><div className="questions">{faq.map(([question, answer]) => <details key={question}><summary>{question}<ChevronDown size={19} aria-hidden="true" /></summary><p>{answer}</p></details>)}</div></div></div></section>
      <section className="closing" aria-labelledby="closing-title"><div className="wrap closing-inner"><div><p className="eyebrow">Open source. Open questions.</p><h2 id="closing-title">Follow the evidence.</h2></div><div className="closing-actions"><Action onClick={() => openModal('start')}>Explore the project <ArrowRight size={18} /></Action><Action href="#evidence" secondary>Read the evidence <ArrowUpRight size={17} /></Action></div></div></section>
    </main>
    <footer className="site-footer alternate"><div className="wrap"><div className="footer-main"><div className="footer-brand"><a className="brand-link" href="#" aria-label="MuleNet home"><Mark /></a><p>Graph-based money-mule detection.<br />Research with its limits in view.</p></div><div className="footer-links"><div><h3>Project</h3><a href="#product">Product</a><a href="#workflow">Workflow</a><a href="#setups">Get started</a></div><div><h3>Evidence</h3><a href="#evidence">Evaluation</a><a href="/evidence.json" download>Source report</a><a href="#questions">Limitations</a></div><div><h3>Open source</h3><a href={REPO}>Repository</a><a href={`${REPO}/issues`}>Issues</a><a href={`${REPO}/blob/main/LICENSE`}>License</a></div></div></div><div className="footer-bottom"><span>© {new Date().getFullYear()} MuleNet contributors</span><span>Not for production decisions.</span><a href={REPO} aria-label="MuleNet on GitHub"><CodeXml size={18} />GitHub<ArrowUpRight size={14} /></a></div></div></footer>
    <dialog ref={dialog} className={`site-dialog ${modal === 'graph' ? 'graph-dialog' : ''}`} aria-labelledby="dialog-title" onClose={() => setModal(null)} onCancel={() => setModal(null)} onClick={event => { if (event.target === event.currentTarget) setModal(null); }}>
      <div className="dialog-top"><span className="eyebrow">{modal === 'graph' ? 'Illustrative evidence / simulated' : 'Run locally / research only'}</span><button className="icon-link" type="button" aria-label="Close dialog" title="Close dialog" onClick={() => setModal(null)}><X /></button></div>
      {modal === 'graph' ? <><h2 id="dialog-title">A path worth reviewing.</h2><div className="dialog-graph-scroll" role="region" aria-label="Illustrative transfer graph" tabIndex={0}><img src="/evidence-graph-alpha.png" width="1737" height="905" alt={graphDescription} /></div><div className="segmented review-steps" aria-label="Illustrative evidence stage">{['Observe', 'Trace', 'Review'].map((label, i) => <button key={label} type="button" aria-pressed={reviewStep === i} onClick={() => setReviewStep(i)}>{label}</button>)}</div><div className="review-explanation" aria-live="polite"><strong>{['An incoming transfer is an observation.', 'Connected transfers add context.', 'A signal needs human review.'][reviewStep]}</strong><p>{['A001 sends to A014. That event alone does not establish wrongdoing.', 'The upper branch passes through A027, A033 and A042. The highlighted relay path is a synthetic example, not a model finding.', 'SOFT_HOLD is an internal, time-limited review state. This illustration does not hold money or make an automated decision.'][reviewStep]}</p></div></> : <><h2 id="dialog-title">Start with the research.</h2><p>Run in an isolated local environment. Read the repository setup and data-license notes before using datasets or starting services.</p><div className="requirements"><Terminal size={19} /><span>Python / uv · Node · Java / Maven · Docker</span></div><pre><code>uv sync --frozen --all-groups{'\n'}uv run python scripts/bootstrap_secrets.py{'\n'}uv run python scripts/eval_smoke.py --allow-synthetic</code></pre><p className="dialog-warning">The smoke run uses simulated data. Full-stack one-command acceptance is unfinished. Security findings remain open. Never reuse placeholder secrets or expose the ML service.</p><Action href={`${REPO}#development`}>Read setup documentation<ArrowUpRight size={17} /></Action></>}
    </dialog>
  </>;
}

createRoot(document.getElementById('root')).render(<StrictMode><Site /></StrictMode>);
