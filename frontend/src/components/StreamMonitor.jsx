import React, { useState, useEffect } from 'react';
import { Activity, Pause, Play, Cpu, Layers, Zap } from 'lucide-react';
import { MetricCard, Spinner, ML_API } from './Common';

export default function StreamMonitor() {
  const [isPlaying, setIsPlaying] = useState(false);
  const [txns, setTxns] = useState([]);
  const [flinkWindows, setFlinkWindows] = useState({});
  const [stats, setStats] = useState({
    totalProcessed: 0,
    anomaliesCount: 0,
    avgRisk: 0,
  });

  useEffect(() => {
    if (!isPlaying) return;

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${ML_API}/api/stream/next`);
        if (!res.ok) throw new Error('API error');
        const data = await res.json();
        
        setTxns(prev => [data, ...prev.slice(0, 14)]); // Keep last 15 txns
        
        // Update stats
        setStats(prev => {
          const nextTotal = prev.totalProcessed + 1;
          const nextAnomalies = prev.anomaliesCount + (data.risk_evaluation.calibrated_risk_score > 60 ? 1 : 0);
          const nextAvgRisk = (prev.avgRisk * prev.totalProcessed + data.risk_evaluation.calibrated_risk_score) / nextTotal;
          return {
            totalProcessed: nextTotal,
            anomaliesCount: nextAnomalies,
            avgRisk: nextAvgRisk
          };
        });

        // Update Flink sliding windows locally based on the incoming transaction
        setFlinkWindows(prev => {
          const next = { ...prev };
          const acct = data.receiver_account;
          
          if (!next[acct]) {
            next[acct] = {
              accountId: acct,
              sender5mCount: new Set(),
              inflow30m: 0,
              outflow60m: 0,
              lastUpdated: Date.now(),
              riskScore: data.risk_evaluation.calibrated_risk_score
            };
          }
          
          // Add sender to Set
          next[acct].sender5mCount.add(data.sender_account);
          next[acct].inflow30m += data.amount;
          next[acct].lastUpdated = Date.now();
          next[acct].riskScore = Math.max(next[acct].riskScore, data.risk_evaluation.calibrated_risk_score);
          
          // Simulate outflow for cash-out velocity
          if (data.risk_evaluation.calibrated_risk_score > 60) {
            next[acct].outflow60m += data.amount * 0.95;
          } else {
            next[acct].outflow60m += data.amount * 0.15;
          }

          // Clean up old windows (simulating eviction after 5 mins/30 mins in Flink)
          // For the sake of the simulation, we only keep the top 10 active ones
          const sorted = Object.values(next).sort((a, b) => b.lastUpdated - a.lastUpdated);
          const cleaned = {};
          sorted.slice(0, 10).forEach(item => {
            cleaned[item.accountId] = item;
          });
          return cleaned;
        });

      } catch (e) {
        console.error('Failed to fetch next stream event:', e);
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [isPlaying]);

  return (
    <div className="main-content">
      {/* Control Header */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2 style={{ fontSize: '18px', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '8px', margin: 0 }}>
              <Activity size={20} className="metric-accent" /> Real-Time UPI Stream Monitor
            </h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '12px', marginTop: '4px', marginBottom: 0 }}>
              Continuous Flink Sliding Aggregations & ML Risk scoring on live Kafka messaging queue.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <div className={`status-pill ${isPlaying ? '' : 'paused'}`} style={{
              background: isPlaying ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)',
              borderColor: isPlaying ? 'rgba(34, 197, 94, 0.3)' : 'rgba(239, 68, 68, 0.3)',
              color: isPlaying ? 'var(--accent-green)' : 'var(--accent-red)'
            }}>
              <div className="status-dot" style={{
                background: isPlaying ? 'var(--accent-green)' : 'var(--accent-red)',
                animation: isPlaying ? 'pulse-green 2s infinite' : 'none'
              }} />
              {isPlaying ? 'RUNNING STREAM' : 'PAUSED'}
            </div>
            <button
              onClick={() => setIsPlaying(!isPlaying)}
              className="btn-analyze"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 16px',
                background: isPlaying ? 'var(--accent-red)' : 'var(--accent-primary)',
                boxShadow: isPlaying ? '0 4px 15px rgba(239,68,68,0.2)' : '0 4px 15px rgba(91,141,239,0.2)',
                border: 'none',
                borderRadius: '8px',
                color: '#fff',
                cursor: 'pointer',
                fontWeight: 600
              }}
            >
              {isPlaying ? (
                <><Pause size={14} /> Pause Ingestion</>
              ) : (
                <><Play size={14} /> Start Ingestion</>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Metrics Bar */}
      <div className="metric-grid">
        <MetricCard label="Transactions Processed" value={stats.totalProcessed} sub="Total UPI ingestion queue" accent="metric-accent" />
        <MetricCard label="Flink Active Windows" value={Object.keys(flinkWindows).length} sub="Feature store sliding keys" accent="metric-orange" />
        <MetricCard label="Avg Pipeline Risk" value={stats.avgRisk?.toFixed(1) + "%"} sub="Calibrated risk index" accent="metric-up" />
        <MetricCard label="Anomalies Intercepted" value={stats.anomaliesCount} sub="High risk (>60) blocks" accent="metric-down" />
      </div>

      {/* Pipeline Diagram */}
      <div className="card" style={{ padding: '20px', background: 'rgba(17, 24, 39, 0.4)' }}>
        <div className="card-header" style={{ marginBottom: '10px' }}>
          <div className="card-title"><Cpu size={14} className="icon" /> Real-Time Decisioning Pipeline</div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px', overflowX: 'auto', padding: '10px 0' }}>
          <div style={{ flex: 1, minWidth: '120px', padding: '12px', background: 'rgba(91, 141, 239, 0.05)', border: '1px solid rgba(91, 141, 239, 0.2)', borderRadius: '8px', textAlign: 'center' }}>
            <div style={{ fontSize: '11px', color: 'var(--accent-primary)', fontWeight: 700 }}>1. UPI STREAM</div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '4px' }}>Real-time Txns Feed</div>
          </div>
          <div style={{ color: 'var(--text-muted)' }}>➔</div>
          <div style={{ flex: 1, minWidth: '120px', padding: '12px', background: isPlaying ? 'rgba(168, 85, 247, 0.1)' : 'rgba(255,255,255,0.01)', border: isPlaying ? '1px dashed var(--accent-purple)' : '1px solid var(--border-subtle)', borderRadius: '8px', textAlign: 'center', transition: 'all 0.3s' }}>
            <div style={{ fontSize: '11px', color: 'var(--accent-purple)', fontWeight: 700 }}>2. KAFKA TOPIC</div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '4px' }}>Buffered Queue</div>
          </div>
          <div style={{ color: 'var(--text-muted)' }}>➔</div>
          <div style={{ flex: 1, minWidth: '120px', padding: '12px', background: isPlaying ? 'rgba(6, 182, 212, 0.1)' : 'rgba(255,255,255,0.01)', border: isPlaying ? '1px dashed var(--accent-cyan)' : '1px solid var(--border-subtle)', borderRadius: '8px', textAlign: 'center', transition: 'all 0.3s' }}>
            <div style={{ fontSize: '11px', color: 'var(--accent-cyan)', fontWeight: 700 }}>3. FLINK SLIDING WINDOWS</div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '4px' }}>Rolling 5m/30m/60m Aggs</div>
          </div>
          <div style={{ color: 'var(--text-muted)' }}>➔</div>
          <div style={{ flex: 1, minWidth: '120px', padding: '12px', background: 'rgba(249, 115, 22, 0.05)', border: '1px solid rgba(249, 115, 22, 0.2)', borderRadius: '8px', textAlign: 'center' }}>
            <div style={{ fontSize: '11px', color: 'var(--accent-orange)', fontWeight: 700 }}>4. ONLINE STORE (REDIS)</div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '4px' }}>Low-latency Feature Store</div>
          </div>
        </div>
      </div>

      {/* Main Stream Display Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.25fr 1fr', gap: '20px' }}>
        
        {/* Flink Aggregations Table */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <Layers size={16} className="icon" /> Flink Stateful Feature Store (Redis Emulator)
            </div>
            <div className="stat-chip">Active Sliding Window Store</div>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-subtle)', textAlign: 'left', color: 'var(--text-muted)' }}>
                  <th style={{ padding: '8px' }}>Account ID</th>
                  <th style={{ padding: '8px' }}>5m Senders</th>
                  <th style={{ padding: '8px' }}>30m Inflow</th>
                  <th style={{ padding: '8px' }}>Velocity (Out/In)</th>
                  <th style={{ padding: '8px', textAlign: 'right' }}>Risk Score</th>
                </tr>
              </thead>
              <tbody>
                {Object.keys(flinkWindows).length === 0 ? (
                  <tr>
                    <td colSpan="5" style={{ padding: '20px 0', textAlign: 'center', color: 'var(--text-muted)' }}>
                      No active Flink windows. Start ingestion to stream data.
                    </td>
                  </tr>
                ) : (
                  Object.values(flinkWindows).map(win => {
                    const ratio = win.inflow30m > 0 ? (win.outflow60m / win.inflow30m).toFixed(2) : '0.00';
                    return (
                      <tr key={win.accountId} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                        <td style={{ padding: '10px', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>{win.accountId}</td>
                        <td style={{ padding: '10px' }}>
                          <span className="stat-chip">{win.sender5mCount.size} senders</span>
                        </td>
                        <td style={{ padding: '10px', fontWeight: 600 }}>₹{win.inflow30m.toLocaleString(undefined, {maximumFractionDigits: 0})}</td>
                        <td style={{ padding: '10px' }}>
                          <span className="stat-chip" style={{
                            borderColor: ratio > 0.8 ? 'rgba(239,68,68,0.3)' : 'var(--border-subtle)',
                            color: ratio > 0.8 ? 'var(--accent-red)' : 'var(--text-secondary)'
                          }}>
                            {ratio}x cash-out
                          </span>
                        </td>
                        <td style={{ padding: '10px', textAlign: 'right', fontWeight: 800 }}>
                          <span style={{
                            color: win.riskScore > 60 ? 'var(--accent-red)' : win.riskScore > 35 ? 'var(--accent-orange)' : 'var(--accent-green)'
                          }}>
                            {win.riskScore.toFixed(0)}
                          </span>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Kafka Event Feed */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', maxHeight: '500px' }}>
          <div className="card-header">
            <div className="card-title">
              <Zap size={16} className="icon" /> Live Kafka Topic Ingestion Queue
            </div>
            <div className="stat-chip">topic: upi.transactions</div>
          </div>
          
          <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '10px', paddingRight: '4px' }}>
            {txns.length === 0 ? (
              <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '40px 0', fontSize: '13px' }}>
                Waiting for incoming events...
              </div>
            ) : (
              txns.map(txn => {
                const isRisk = txn.risk_evaluation.calibrated_risk_score > 60;
                return (
                  <div key={txn.utr} style={{
                    background: 'var(--bg-elevated)',
                    border: '1px solid var(--border-subtle)',
                    borderLeft: `4px solid ${isRisk ? 'var(--accent-red)' : 'var(--accent-primary)'}`,
                    borderRadius: '6px',
                    padding: '10px 14px',
                    fontSize: '11px',
                    animation: 'fadeSlideIn 0.3s ease-out',
                    boxShadow: isRisk ? '0 0 15px rgba(239,68,68,0.1)' : 'none'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{txn.utr}</span>
                      <span style={{ fontWeight: 800, color: 'var(--text-primary)' }}>
                        ₹{txn.amount.toLocaleString(undefined, {minimumFractionDigits: 2})}
                      </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ color: 'var(--text-secondary)' }}>
                        <strong style={{ color: 'var(--text-primary)' }}>{txn.sender_account}</strong>
                        {' ➔ '}
                        <strong style={{ color: 'var(--text-primary)' }}>{txn.receiver_account}</strong>
                      </div>
                      <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                        <span style={{ color: 'var(--text-muted)' }}>📱 {txn.device_id?.split('-')[-1] || txn.device_id}</span>
                        <span style={{
                          fontWeight: 700,
                          color: isRisk ? 'var(--accent-red)' : 'var(--accent-green)',
                          background: isRisk ? 'rgba(239, 68, 68, 0.1)' : 'rgba(34, 197, 94, 0.1)',
                          padding: '1px 5px',
                          borderRadius: '3px'
                        }}>
                          {txn.risk_evaluation.calibrated_risk_score.toFixed(0)}
                        </span>
                      </div>
                    </div>
                    {isRisk && (
                      <div style={{ marginTop: '4px', color: 'var(--accent-orange)', fontWeight: 600 }}>
                        ⚠ Alert: {txn.risk_evaluation.anomaly_reason}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
