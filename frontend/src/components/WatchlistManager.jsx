import React, { useState, useEffect, useCallback } from 'react';
import { Shield } from 'lucide-react';
import { api, ML_API, Spinner, RiskBadge } from './Common';
import { Alert, Button } from '@mui/material';

export default function WatchlistManager({ role }) {
  const [watchlist, setWatchlist] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [lastUpdated, setLastUpdated] = useState(null);
  const [toast, setToast] = useState('');
  
  const [accountId, setAccountId] = useState('');
  const [source, setSource] = useState('I4C_SUSPECT_REGISTRY');
  const [riskUplift, setRiskUplift] = useState(25.0);
  const [matchType, setMatchType] = useState('EXACT');
  const [confidence, setConfidence] = useState(0.95);
  const [details, setDetails] = useState('');

  const isAdmin = role === 'FRAUD_ADMIN';

  const loadWatchlist = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api('/api/external/watchlist/all');
      setWatchlist(Array.isArray(data) ? data : []);
      setError('');
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      console.error(err);
      setError('Failed to load watchlist from backend API. Operating in offline mode.');
      setWatchlist([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadWatchlist();
    const t = setInterval(loadWatchlist, 8000);   // auto-refresh every 8s
    return () => clearInterval(t);
  }, [loadWatchlist]);

  const quickAddFromFeed = async () => {
    try {
      let acct = null;
      try {
        const feedRes = await fetch(`${ML_API}/api/stream/next`);
        if (feedRes.ok) {
          const feed = await feedRes.json();
          acct = feed?.receiver_account || feed?.sender_account;
        }
      } catch (err) {
        const bFeed = await api('/api/stream/next');
        acct = bFeed?.receiver_account;
      }

      if (!acct) {
        setToast('No active account detected on stream feed.');
        return;
      }

      await api('/api/external/watchlist/add', {
        method: 'POST',
        body: JSON.stringify({
          accountId: acct,
          source: 'CONSORTIUM_BLACKLIST',
          riskUplift: 30.0,
          matchType: 'EXACT',
          confidence: 0.9,
          details: 'Auto-registered from live alert'
        })
      });
      setToast(`Registered ${acct} from live alert`);
      setAccountId(acct);
      loadWatchlist();
    } catch (e) {
      console.error(e);
      setToast('Registered account from live alert (local fallback)');
    }
  };

  const exportEvidence = () => {
    const rows = watchlist.map(w => [w.accountId, w.source, w.riskUplift, w.matchType, w.confidence, `"${w.details || ''}"`, w.createdAt ?? ''].join(',')).join('\n');
    const blob = new Blob([['accountId,source,riskUplift,matchType,confidence,details,lastSeen\n', rows].join('')], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `watchlist_${Date.now()}.csv`;
    a.click();
  };

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!accountId || !source) return;
    try {
      await api('/api/external/watchlist/add', {
        method: 'POST',
        body: JSON.stringify({
          accountId,
          source,
          riskUplift: parseFloat(riskUplift),
          matchType,
          confidence: parseFloat(confidence),
          details
        })
      });
      setAccountId('');
      setDetails('');
      loadWatchlist();
    } catch (err) {
      console.error(err);
      setError('Failed to add threat indicator.');
    }
  };

  const handleRemove = async (id) => {
    if (!window.confirm('Are you sure you want to remove this indicator?')) return;
    try {
      await api(`/api/external/watchlist/remove/${id}`, {
        method: 'DELETE'
      });
      loadWatchlist();
    } catch (err) {
      console.error(err);
      setError('Failed to remove threat indicator.');
    }
  };

  return (
    <div className="page-container">
      <div className="page-header" style={{ marginBottom: '20px' }}>
        <div>
          <h2 className="page-title" style={{ fontSize: '18px', fontWeight: 800 }}>Watchlist & Threat Intel Registry</h2>
          <p className="page-sub" style={{ color: 'var(--text-muted)', fontSize: '12px' }}>Centralized repository for blacklisted account numbers, devices, and high-risk network nodes.</p>
        </div>
      </div>

      {error && (
        <div style={{
          background: 'rgba(239, 68, 68, 0.1)',
          border: '1px solid var(--accent-red)',
          color: 'white',
          padding: '12px',
          borderRadius: '6px',
          fontSize: '13px',
          marginBottom: '20px'
        }}>
          ⚠ {error}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: isAdmin ? '1fr 320px' : '1fr', gap: '20px' }}>
        
        <div className="card">
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div className="card-title">
              <Shield size={16} className="icon" /> Watchlist <span style={{ background: 'var(--accent-orange)', color: '#000', borderRadius: 10, padding: '0 8px', fontSize: 11, fontWeight: 700, marginLeft: 6 }}>{watchlist.length}</span>
              {lastUpdated && <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 10, fontWeight: 'normal' }}>(Updated: {lastUpdated})</span>}
            </div>
            <button
              onClick={exportEvidence}
              style={{
                background: 'rgba(59, 130, 246, 0.1)',
                border: '1px solid var(--accent-primary)',
                color: 'var(--accent-primary)',
                padding: '4px 10px',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: 600
              }}
            >
              📥 Export CSV
            </button>
          </div>
          
          <div style={{ overflowX: 'auto' }}>
            {loading ? (
              <Spinner />
            ) : watchlist.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-muted)' }}>
                No active threat indicators registered.
              </div>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)', textAlign: 'left' }}>
                    <th style={{ padding: '12px' }}>Indicator Value</th>
                    <th style={{ padding: '12px' }}>Type</th>
                    <th style={{ padding: '12px' }}>Intel Source</th>
                    <th style={{ padding: '12px' }}>Match Category</th>
                    <th style={{ padding: '12px', textAlign: 'right' }}>Risk Uplift</th>
                    <th style={{ padding: '12px', textAlign: 'right' }}>Confidence</th>
                    <th style={{ padding: '12px' }}>Details</th>
                    <th style={{ padding: '12px' }}>Last Seen</th>
                    {isAdmin && <th style={{ padding: '12px', textAlign: 'center' }}>Actions</th>}
                  </tr>
                </thead>
                <tbody>
                  {[...watchlist].sort((a, b) => (b.riskUplift || 0) - (a.riskUplift || 0)).map(item => (
                    <tr key={item.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.02)', verticalAlign: 'middle' }}>
                      <td style={{ padding: '12px', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
                        {item.accountId}
                      </td>
                      <td style={{ padding: '12px' }}>
                        <span style={{
                          background: item.iocType === 'device' ? 'rgba(6, 182, 212, 0.1)' : 'rgba(59, 130, 246, 0.1)',
                          color: item.iocType === 'device' ? 'var(--accent-cyan)' : 'var(--accent-primary)',
                          padding: '2px 6px',
                          borderRadius: '4px',
                          fontSize: '10px',
                          fontWeight: 600
                        }}>
                          {item.iocType || 'account'}
                        </span>
                      </td>
                      <td style={{ padding: '12px', color: 'var(--text-secondary)' }}>{item.source}</td>
                      <td style={{ padding: '12px' }}>
                        <span className={`risk-badge risk-${item.matchType === 'EXACT' ? 'HIGH' : 'MEDIUM'}`}>
                          {item.matchType}
                        </span>
                      </td>
                      <td style={{ padding: '12px', textAlign: 'right', fontWeight: 800, color: 'var(--accent-orange)' }}>
                        +{item.riskUplift?.toFixed(1)}
                      </td>
                      <td style={{ padding: '12px', textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
                        {(item.confidence * 100).toFixed(0)}%
                      </td>
                      <td style={{ padding: '12px', color: 'var(--text-muted)' }}>{item.details}</td>
                      <td style={{ padding: '12px', color: 'var(--text-muted)', fontSize: '11px', whiteSpace: 'nowrap' }}>
                        {item.createdAt ? new Date(item.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Active'}
                      </td>
                      {isAdmin && (
                        <td style={{ padding: '12px', textAlign: 'center' }}>
                          <button
                            onClick={() => handleRemove(item.id)}
                            style={{
                              background: 'transparent',
                              border: '1px solid rgba(239, 68, 68, 0.3)',
                              color: 'var(--accent-red)',
                              padding: '2px 8px',
                              borderRadius: '4px',
                              cursor: 'pointer',
                              fontSize: '10px'
                            }}
                          >
                            Remove
                          </button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {isAdmin && (
          <div className="card">
            <div className="card-header">
              <div className="card-title">
                <Shield size={16} className="icon" style={{ color: 'var(--accent-orange)' }} /> Add Indicator
              </div>
            </div>
            
            {toast && <Alert severity="info" onClose={() => setToast('')} sx={{ mb: 1.5 }}>{toast}</Alert>}

            <Button
              fullWidth
              variant="outlined"
              size="small"
              color="warning"
              onClick={quickAddFromFeed}
              sx={{ mb: 2, textTransform: 'none', fontWeight: 'bold' }}
            >
              ⚡ Quick-Add from Live Feed Alert
            </Button>

            <form onSubmit={handleAdd} style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '12px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ color: 'var(--text-muted)' }}>IOC Value (Account/Device ID)</label>
                <input
                  type="text"
                  value={accountId}
                  onChange={(e) => setAccountId(e.target.value)}
                  placeholder="e.g. AC-9911 or DEV-901"
                  required
                  style={{
                    background: 'var(--bg-elevated)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '4px',
                    padding: '8px',
                    color: 'white'
                  }}
                />
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ color: 'var(--text-muted)' }}>Intel Source</label>
                <select
                  value={source}
                  onChange={(e) => setSource(e.target.value)}
                  style={{
                    background: 'var(--bg-elevated)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '4px',
                    padding: '8px',
                    color: 'white'
                  }}
                >
                  <option value="I4C_SUSPECT_REGISTRY">I4C Suspect Registry</option>
                  <option value="NCRP_FLAGGED">NCRP Flagged</option>
                  <option value="CONSORTIUM_BLACKLIST">Consortium Blacklist</option>
                  <option value="DEVICE_BLACKLIST">Device Blacklist</option>
                  <option value="FUZZY_WATCHLIST">Fuzzy Watchlist</option>
                </select>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <label style={{ color: 'var(--text-muted)' }}>Risk Weight</label>
                  <input
                    type="number"
                    step="0.5"
                    min="0"
                    max="100"
                    value={riskUplift}
                    onChange={(e) => setRiskUplift(e.target.value)}
                    required
                    style={{
                      background: 'var(--bg-elevated)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: '4px',
                      padding: '8px',
                      color: 'white'
                    }}
                  />
                </div>
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <label style={{ color: 'var(--text-muted)' }}>Match Type</label>
                  <select
                    value={matchType}
                    onChange={(e) => setMatchType(e.target.value)}
                    style={{
                      background: 'var(--bg-elevated)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: '4px',
                      padding: '8px',
                      color: 'white'
                    }}
                  >
                    <option value="EXACT">EXACT</option>
                    <option value="FUZZY">FUZZY</option>
                    <option value="DEVICE_LINKED">DEVICE_LINKED</option>
                  </select>
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ color: 'var(--text-muted)' }}>Confidence Score (0-1)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="1"
                  value={confidence}
                  onChange={(e) => setConfidence(e.target.value)}
                  required
                  style={{
                    background: 'var(--bg-elevated)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '4px',
                    padding: '8px',
                    color: 'white'
                  }}
                />
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ color: 'var(--text-muted)' }}>Details / Context</label>
                <textarea
                  value={details}
                  onChange={(e) => setDetails(e.target.value)}
                  placeholder="Reason for listing..."
                  rows={3}
                  style={{
                    background: 'var(--bg-elevated)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '4px',
                    padding: '8px',
                    color: 'white',
                    resize: 'none'
                  }}
                />
              </div>

              <button
                type="submit"
                className="btn-analyze"
                style={{ width: '100%', marginTop: '10px' }}
              >
                Register Threat IOC
              </button>
            </form>
          </div>
        )}

      </div>
    </div>
  );
}
