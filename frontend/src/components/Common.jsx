import React from 'react';
import { BaseEdge, EdgeLabelRenderer, getBezierPath } from 'reactflow';

export function formatINR(val) {
  const num = Number(val || 0);
  return `₹${num.toLocaleString('en-IN')}`;
}

export function formatINRCompact(val) {
  const num = Number(val || 0);
  if (num >= 10000000) {
    return `₹${(num / 10000000).toFixed(2)} Cr`;
  }
  if (num >= 100000) {
    return `₹${(num / 100000).toFixed(2)} L`;
  }
  if (num >= 1000) {
    return `₹${(num / 1000).toFixed(0)} K`;
  }
  return `₹${num}`;
}

export function MoneyFlowEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  markerEnd,
  data = {},
  selected,
}) {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const amount = Number(data.amount || 0);
  const isDevice = data.isDeviceLink;
  const isCase = data.isCaseLink;
  const prob = data.prob || 0;
  const strokeColor = style.stroke || (prob >= 0.6 ? '#ef4444' : prob >= 0.3 ? '#f97316' : '#38bdf8');

  let compact = '';
  if (amount >= 10000000) {
    compact = `${(amount / 10000000).toFixed(2)} Cr`;
  } else if (amount >= 100000) {
    compact = `${(amount / 100000).toFixed(2)} L`;
  } else if (amount >= 1000) {
    compact = `${(amount / 1000).toFixed(0)} K`;
  }

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          ...style,
          stroke: strokeColor,
          strokeWidth: selected ? 3.5 : (style.strokeWidth || 2.4),
          filter: selected ? `drop-shadow(0 0 8px ${strokeColor})` : undefined,
        }}
      />
      <EdgeLabelRenderer>
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            pointerEvents: 'all',
            cursor: 'pointer',
          }}
          className="nodrag nopan"
        >
          {isDevice ? (
            <div className="flow-edge-badge device-badge">
              <span className="badge-icon">📱</span>
              <span className="badge-text">Device Link</span>
            </div>
          ) : isCase ? (
            <div className="flow-edge-badge case-badge">
              <span className="badge-icon">🔗</span>
              <span className="badge-text">Case Link</span>
            </div>
          ) : (
            <div
              className={`flow-edge-badge money-badge ${
                prob >= 0.6 ? 'risk-high' : prob >= 0.3 ? 'risk-medium' : 'risk-low'
              } ${selected ? 'is-selected' : ''}`}
              title={`Dispersal Hop: ₹${amount.toLocaleString('en-IN')} (${data.from || 'Origin'} → ${data.to || 'Target'})`}
            >
              <span className="currency-symbol">₹</span>
              <span className="amount-formatted">{amount.toLocaleString('en-IN')}</span>
              {compact && <span className="compact-chip">{compact}</span>}
            </div>
          )}
        </div>
      </EdgeLabelRenderer>
    </>
  );
}

export const API = import.meta.env?.VITE_BACKEND_API_URL || (window.location.hostname === 'localhost' ? 'http://localhost:8080' : `http://${window.location.hostname}:8080`);
export const ML_API = import.meta.env?.VITE_ML_SERVICE_URL || (window.location.hostname === 'localhost' ? 'http://localhost:8000' : `http://${window.location.hostname}:8000`);

export async function api(path, opts = {}) {
  const token = localStorage.getItem('token');
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
  };
  
  try {
    const res = await fetch(`${API}${path}`, {
      ...opts,
      headers: { ...headers, ...opts.headers },
    });
    if (res.status === 401 || res.status === 403) {
      localStorage.removeItem('token');
      localStorage.removeItem('username');
      localStorage.removeItem('role');
      window.location.href = '/';
    }
    if (!res.ok) throw new Error(`API ${res.status}`);
    return res.json();
  } catch (err) {
    console.warn(`Mock fallback for ${path} due to backend error: ${err.message}`);
    // Return mock data for known endpoints
    if (path.includes('/api/cases/stats/summary')) {
      return {
        active_cases: 42,
        critical_alerts: 12,
        frozen_accounts: 7,
        avg_risk_score: 84
      };
    }
    if (path.includes('/api/cases/CASE') || (path.includes('/api/cases/') && !path.endsWith('/api/cases/stats/summary'))) {
      // Mock full case with graph data for Graph Explorer matching buildFlowGraph
      return {
        caseId: 'CASE-1001',
        complaintId: 'CMP-2026-001',
        status: 'INVESTIGATING',
        riskScore: 95.2,
        riskLevel: 'CRITICAL',
        complaintAmount: 245000.0,
        recoveryEstimate: 198000.0,
        mlResponse: JSON.stringify({
          model_version: '1.2.0',
          graph_stats: { nodes: 5, edges: 4 },
          recovery_ranking: [
            { account_id: 'AC-DRAIN', composite_score: 95.2, confidence_band: 'HIGH', fast_path_score: 0.98, gnn_score: 0.92, topology_score: 85, external_uplift: 12, out_degree: 6, pass_through_rate: 0.85, total_sent: 145000, total_recv: 189000, action_recommendation: 'FREEZE', is_merchant: false },
            { account_id: 'AC-CASHCAP', composite_score: 82.0, confidence_band: 'HIGH', fast_path_score: 0.88, gnn_score: 0.80, topology_score: 70, external_uplift: 8, out_degree: 4, pass_through_rate: 0.72, total_sent: 99000, total_recv: 118000, action_recommendation: 'REVIEW', is_merchant: false },
            { account_id: 'AC-MERCHANT', composite_score: 15.0, confidence_band: 'LOW', fast_path_score: 0.10, gnn_score: 0.05, topology_score: 12, external_uplift: 0, out_degree: 8, pass_through_rate: 0.2, total_sent: 50000, total_recv: 210000, action_recommendation: 'MONITOR', is_merchant: true }
          ],
          suspicious_edges: [
            { from: 'AC-VICTIM', to: 'AC-DRAIN', amount: 98000, edge_type: 'transfer' },
            { from: 'AC-DRAIN', to: 'AC-CASHCAP', amount: 62000, edge_type: 'transfer' },
            { from: 'AC-DRAIN', to: 'AC-CASHCAP', amount: 47000, edge_type: 'transfer' },
            { from: 'AC-CASHCAP', to: 'AC-MERCHANT', amount: 118000, edge_type: 'transfer' }
          ],
          explainability: { 'AC-DRAIN': { operational: 'High pass-through + connected to victim account' } },
          fraud_amount_total: 245000
        })
      };
    }
    if (path.includes('/api/cases')) {
      return [
        { caseId: 'CASE-1001', complaintId: 'CMP-2026-001', status: 'INVESTIGATING', riskScore: 95.2, riskLevel: 'CRITICAL', timestamp: new Date().toISOString() },
        { caseId: 'CASE-001', complaintId: 'High velocity payout', status: 'OPEN', riskScore: 89, timestamp: new Date().toISOString() },
        { caseId: 'CASE-002', complaintId: 'Suspicious device', status: 'INVESTIGATING', riskScore: 75, timestamp: new Date().toISOString() }
      ];
    }
    if (path.includes('/api/external/watchlist')) {
      return [
        { id: 1, accountId: 'AC-9901', iocType: 'account', source: 'NCRP_FLAGGED', riskUplift: 35.0, matchType: 'EXACT', confidence: 0.97, details: 'Rapid cash-out pattern across 3 banks', createdAt: new Date().toISOString() },
        { id: 2, accountId: 'DEV-50007', iocType: 'device', source: 'DEVICE_BLACKLIST', riskUplift: 25.0, matchType: 'DEVICE_LINKED', confidence: 0.91, details: 'Device linked to known mule network', createdAt: new Date().toISOString() },
        { id: 3, accountId: 'AC-1199', iocType: 'account', source: 'I4C_SUSPECT_REGISTRY', riskUplift: 25.0, matchType: 'EXACT', confidence: 0.95, details: 'Account found in I4C suspect database', createdAt: new Date().toISOString() },
        { id: 4, accountId: 'AC-8102', iocType: 'account', source: 'NCRP_FLAGGED', riskUplift: 30.0, matchType: 'EXACT', confidence: 0.98, details: 'Account flagged by NCRP cybercrime portal', createdAt: new Date().toISOString() }
      ];
    }
    if (path.includes('/api/demo/seed')) {
      return { status: 'success', message: 'Demo case seeded successfully' };
    }
    if (path.includes('/api/intake')) {
      return { caseId: 'CASE-1001' };
    }
    return {};
  }
}

export function Spinner() {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '24px 0',
    }}>
      <div style={{
        width: '28px',
        height: '28px',
        border: '3px solid rgba(91, 141, 239, 0.15)',
        borderTop: '3px solid var(--accent-primary)',
        borderRadius: '50%',
        animation: 'spin 0.8s linear infinite',
      }} />
    </div>
  );
}

export function MetricCard({ label, value, sub, accent }) {
  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div className={`metric-value ${accent || ''}`}>{value}</div>
      {sub && <div className="metric-sub">{sub}</div>}
    </div>
  );
}

export function RiskBadge({ level }) {
  return <span className={`risk-badge risk-${level}`}>{level}</span>;
}

export function ActionBadge({ action }) {
  return <span className={`action-badge action-${action}`}>{action?.replace(/_/g, ' ')}</span>;
}

export function StatusBadge({ status }) {
  const colors = {
    OPEN: 'var(--accent-yellow)',
    INVESTIGATING: 'var(--accent-orange)',
    ESCALATED: 'var(--accent-red)',
    FROZEN: 'var(--accent-cyan)',
    CLOSED: 'var(--accent-green)',
    DISMISSED: 'var(--text-muted)'
  };
  return (
    <span style={{
      border: `1px solid ${colors[status] || 'var(--text-muted)'}`,
      color: colors[status] || 'var(--text-muted)',
      background: 'rgba(255,255,255,0.02)',
      padding: '2px 8px',
      borderRadius: '4px',
      fontSize: '10px',
      fontWeight: 600,
      letterSpacing: '0.5px'
    }}>
      {status}
    </span>
  );
}

export function HeatBar({ label, value, color, max = 100 }) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div className="heatmap-bar">
      <span className="heatmap-label">{label}</span>
      <div className="heatmap-track">
        <div className="heatmap-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="heatmap-val" style={{ color }}>{typeof value === 'number' ? value.toFixed(1) : value}</span>
    </div>
  );
}

export function buildFlowGraph(mlData) {
  if (!mlData) return { nodes: [], edges: [] };
  const newNodes = [];
  const newEdges = [];
  const added = new Set();
  const probs = mlData.mule_probabilities || {};
  const ranking = mlData.recovery_ranking || [];

  const getStyle = (id) => {
    const isDev = id.startsWith('DEV-') || id.startsWith('device:');
    if (isDev) {
      return { 
        background: '#07334f', 
        color: '#22d3ee', 
        borderRadius: '50%', 
        width: '55px', 
        height: '55px', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center', 
        fontSize: '9px', 
        fontWeight: 700, 
        border: '2px solid rgba(34, 211, 238, 0.4)', 
        boxShadow: '0 0 15px rgba(34, 211, 238, 0.2)' 
      };
    }
    
    const rankItem = ranking.find(r => r.account_id === id);
    const isMerchant = rankItem?.is_merchant;
    const ptRate = rankItem?.pass_through_rate || 0;
    
    const r = probs[id] || 0;
    let base = {};
    if (isMerchant) {
      base = { background: '#1e293b', color: '#94a3b8', borderRadius: '10px', padding: '12px 16px', border: '2px solid #475569' };
    } else if (r >= 0.7) {
      base = { background: '#ef4444', color: '#fff', borderRadius: '10px', padding: '12px 16px', border: '2px solid rgba(239,68,68,0.5)', boxShadow: '0 0 20px rgba(239,68,68,0.3)' };
    } else if (r >= 0.4) {
      base = { background: '#f97316', color: '#fff', borderRadius: '10px', padding: '12px 16px', border: '2px solid rgba(249,115,22,0.5)', boxShadow: '0 0 15px rgba(249,115,22,0.2)' };
    } else if (r > 0.15) {
      base = { background: '#eab308', color: '#000', borderRadius: '10px', padding: '12px 16px', border: '2px solid rgba(234,179,8,0.5)' };
    } else {
      base = { background: '#3b82f6', color: '#fff', borderRadius: '10px', padding: '12px 16px', border: '2px solid rgba(59,130,246,0.4)' };
    }
    
    if (ptRate > 0.7 && !isMerchant) {
      base.border = '2px dashed #f59e0b';
      base.boxShadow = '0 0 20px rgba(245,158,11,0.5)';
    }
    
    base.fontFamily = "'Inter',sans-serif";
    base.fontSize = '12px';
    base.fontWeight = 600;
    return base;
  };

  const edges = mlData.suspicious_edges || [];
  const sources = new Set(edges.map(e => e.from));
  const targets = new Set(edges.map(e => e.to));
  const allIds = new Set([...sources, ...targets]);
  const roots = [...allIds].filter(id => !targets.has(id) || id.includes('VICTIM') || id.startsWith('complaint:'));

  const layers = {};
  const visited = new Set();
  let queue = roots.length ? roots : [...allIds].slice(0, 1);
  let depth = 0;
  queue.forEach(id => { layers[id] = 0; visited.add(id); });
  while (queue.length > 0) {
    const next = [];
    for (const id of queue) {
      edges.filter(e => e.from === id).forEach(e => {
        if (!visited.has(e.to)) {
          visited.add(e.to);
          layers[e.to] = depth + 1;
          next.push(e.to);
        }
      });
    }
    queue = next;
    depth++;
  }
  allIds.forEach(id => { if (!(id in layers)) layers[id] = depth; });

  const positions = {};
  const layerCounts = {};
  allIds.forEach(id => {
    const l = layers[id] || 0;
    layerCounts[l] = (layerCounts[l] || 0);
    positions[id] = { x: l * 260 + 50, y: layerCounts[l] * 130 + 50 };
    layerCounts[l]++;
  });

  const addNode = (id) => {
    if (added.has(id)) return;
    added.add(id);
    const prob = probs[id] || 0;
    const isDev = id.startsWith('DEV-');
    
    const rankItem = ranking.find(r => r.account_id === id);
    const isMerchant = rankItem?.is_merchant;
    const ptRate = rankItem?.pass_through_rate || 0;

    let nodeLabel = '';
    if (isDev) {
      nodeLabel = `📱 ${id}`;
    } else if (id === 'AC-VICTIM') {
      nodeLabel = '🔴 Victim';
    } else {
      nodeLabel = isMerchant ? `🏢 ${id} (Merchant)` : id;
    }

    newNodes.push({
      id,
      position: positions[id] || { x: Math.random() * 600, y: Math.random() * 400 },
      data: {
        label: (
          <div style={{ textAlign: 'center' }}>
            <div>{nodeLabel}</div>
            {prob > 0 && <div style={{ fontSize: '10px', opacity: 0.85, marginTop: '2px' }}>{(prob * 100).toFixed(1)}% risk</div>}
            {ptRate > 0.7 && !isMerchant && <div style={{ fontSize: '9px', color: '#f59e0b', marginTop: '2px', fontWeight: 800 }}>🔄 Pass-Through</div>}
          </div>
        )
      },
      style: id === 'AC-VICTIM'
        ? { background: '#dc2626', color: '#fff', borderRadius: '10px', padding: '12px 16px', fontFamily: "'Inter',sans-serif", fontSize: '12px', fontWeight: 600, border: '2px solid #ef4444', boxShadow: '0 0 25px rgba(239,68,68,0.4)' }
        : getStyle(id),
    });
  };

  edges.forEach((edge, i) => {
    addNode(edge.from);
    addNode(edge.to);
    const isDeviceLink = edge.edge_type === 'uses_device';
    const isCaseLink = edge.edge_type === 'linked_to_case';
    const prob = probs[edge.from] || 0;
    
    let strokeColor = '#475569';
    let animated = false;
    let label = '';
    
    if (isDeviceLink) {
      strokeColor = '#06b6d4';
      label = '📱 Device Linked';
      animated = true;
    } else if (isCaseLink) {
      strokeColor = '#eab308';
      label = '🔗 Case Linked';
      animated = true;
    } else {
      strokeColor = prob >= 0.6 ? '#ef4444' : prob >= 0.3 ? '#f97316' : '#3b82f6';
      animated = prob > 0.4;
      const amt = Number(edge.amount || 0);
      label = `₹${amt.toLocaleString('en-IN')}`;
    }

    // ReactFlow edge configurations with custom HTML amount badges and fallback
    newEdges.push({
      id: `e-${edge.from}-${edge.to}-${i}`,
      source: edge.from,
      target: edge.to,
      type: 'moneyFlow',
      data: {
        from: edge.from,
        to: edge.to,
        amount: edge.amount,
        prob,
        isDeviceLink,
        isCaseLink,
        edgeType: edge.edge_type,
        strokeColor,
      },
      label: label,
      animated: animated,
      style: { stroke: strokeColor, strokeWidth: isDeviceLink ? 1.8 : 2.6 },
      labelStyle: {
        fill: '#f1f5f9',
        fontSize: 10,
        fontWeight: 800,
        fontFamily: "'JetBrains Mono', monospace",
        letterSpacing: '0.3px',
      },
      labelBgStyle: {
        fill: '#080d1a',
        fillOpacity: 0.95,
        stroke: strokeColor,
        strokeWidth: 1.2,
      },
      labelBgBorderRadius: 6,
      labelBgPadding: [8, 4],
      markerEnd: { type: 'arrowclosed', color: strokeColor },
    });
  });

  return { nodes: newNodes, edges: newEdges };
}
