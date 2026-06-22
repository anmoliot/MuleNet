import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import {
  ShieldAlert, Activity, Network, BarChart3, Settings, Shield, Bell, X
} from 'lucide-react';

import Login from './components/Login';
import Dashboard from './components/Dashboard';
import StreamMonitor from './components/StreamMonitor';
import CaseDetail from './components/CaseDetail';
import GraphExplorer from './components/GraphExplorer';
import PolicyConfig from './components/PolicyConfig';
import AuditLedger from './components/AuditLedger';
import WatchlistManager from './components/WatchlistManager';
import UserManagement from './components/UserManagement';
import Governance from './components/Governance';
import { API } from './components/Common';

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [username, setUsername] = useState(localStorage.getItem('username'));
  const [role, setRole] = useState(localStorage.getItem('role'));
  const [alerts, setAlerts] = useState([]);
  const [showAlertsMenu, setShowAlertsMenu] = useState(false);
  const [toast, setToast] = useState(null);

  useEffect(() => {
    if (!token) return;
    const url = `${API}/api/notifications/subscribe?token=${token}`;
    const eventSource = new EventSource(url);

    eventSource.addEventListener('alert', (e) => {
      try {
        const alertData = JSON.parse(e.data);
        setAlerts(prev => [alertData, ...prev.slice(0, 9)]);
        setToast(alertData);
        setTimeout(() => setToast(null), 6000);
      } catch (err) {
        console.error("Failed to parse alert payload:", err);
      }
    });

    eventSource.onerror = (err) => {
      console.error("SSE connection error, retrying...", err);
    };

    return () => {
      eventSource.close();
    };
  }, [token]);

  const handleLoginSuccess = (t, u, r) => {
    setToken(t);
    setUsername(u);
    setRole(r);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    localStorage.removeItem('role');
    setToken(null);
    setUsername(null);
    setRole(null);
  };

  if (!token) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  const isSupervisorOrCompliance = role === 'SUPERVISOR' || role === 'COMPLIANCE_OFFICER';
  const isFraudAdmin = role === 'FRAUD_ADMIN';

  return (
    <BrowserRouter>
      <div className="app-shell">
        {/* Topbar */}
        <header className="topbar">
          <div className="topbar-brand">
            <div className="logo-icon">🛡</div>
            <div>
              <h1>MuleNet</h1>
              <span>Graph-Native Fraud Intelligence</span>
            </div>
          </div>
          <div className="topbar-right">
            {/* Live Alerts Bell */}
            <div style={{ position: 'relative', marginRight: '15px', cursor: 'pointer', display: 'flex', alignItems: 'center' }} onClick={() => setShowAlertsMenu(!showAlertsMenu)}>
              <Bell size={18} style={{ color: alerts.length > 0 ? 'var(--accent-red)' : 'var(--text-secondary)' }} />
              {alerts.length > 0 && (
                <span style={{
                  position: 'absolute',
                  top: '-4px',
                  right: '-4px',
                  background: 'var(--accent-red)',
                  color: 'white',
                  borderRadius: '50%',
                  width: '12px',
                  height: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '8px',
                  fontWeight: 700
                }}>
                  {alerts.length}
                </span>
              )}
              {showAlertsMenu && (
                <div style={{
                  position: 'absolute',
                  top: '30px',
                  right: '0',
                  background: 'rgba(19, 28, 46, 0.95)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '8px',
                  padding: '12px',
                  width: '280px',
                  zIndex: 200,
                  boxShadow: '0 10px 25px rgba(0,0,0,0.5)',
                  backdropFilter: 'blur(10px)',
                  textAlign: 'left'
                }} onClick={(e) => e.stopPropagation()}>
                  <div style={{ fontWeight: 700, fontSize: '11px', marginBottom: '8px', color: 'var(--text-primary)', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '4px' }}>
                    Live Notifications Queue
                  </div>
                  {alerts.length === 0 ? (
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)', textAlign: 'center', padding: '10px 0' }}>No new notifications</div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '200px', overflowY: 'auto' }}>
                      {alerts.map((a, idx) => (
                        <div key={idx} style={{ fontSize: '10px', borderBottom: idx < alerts.length - 1 ? '1px solid rgba(255,255,255,0.02)' : 'none', paddingBottom: '6px' }}>
                          <div style={{ color: a.severity === 'HIGH' ? 'var(--accent-red)' : 'var(--accent-orange)', fontWeight: 700 }}>{a.title}</div>
                          <div style={{ color: 'var(--text-secondary)', marginTop: '2px', lineHeight: '1.3' }}>{a.message}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            <span style={{
              fontSize: '11px',
              color: 'var(--text-muted)',
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '4px',
              padding: '4px 8px',
              marginRight: '10px',
              fontFamily: 'var(--font-mono)'
            }}>
              👤 {username} ({role})
            </span>
            <button
              className="btn-analyze"
              onClick={handleLogout}
              style={{
                padding: '5px 12px',
                fontSize: '11px',
                background: 'transparent',
                border: '1px solid var(--border-subtle)',
                marginRight: '15px'
              }}
            >
              Sign Out
            </button>
            <div className="status-pill"><div className="status-dot" /> LIVE</div>
          </div>
        </header>

        {/* Sidebar */}
        <nav className="sidebar">
          <div className="sidebar-section-label">Intelligence</div>
          <NavLink to="/" end className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <Activity size={15} className="nav-icon" /> Dashboard
          </NavLink>
          <NavLink to="/stream" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <Activity size={15} className="nav-icon" style={{ color: 'var(--accent-cyan)' }} /> Stream Monitor
          </NavLink>
          <NavLink to="/explorer" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <Network size={15} className="nav-icon" /> Graph Explorer
          </NavLink>
          <NavLink to="/watchlist" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <Shield size={15} className="nav-icon" style={{ color: 'var(--accent-orange)' }} /> Watchlist Registry
          </NavLink>

          <div className="sidebar-section-label">Operations</div>
          <NavLink to="/policy" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <Settings size={15} className="nav-icon" /> Policy Config
          </NavLink>
          {isSupervisorOrCompliance && (
            <NavLink to="/audit" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <ShieldAlert size={15} className="nav-icon" /> Audit Ledger
            </NavLink>
          )}
          <NavLink to="/governance" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <BarChart3 size={15} className="nav-icon" /> Governance
          </NavLink>

          {isFraudAdmin && (
            <>
              <div className="sidebar-section-label">Administration</div>
              <NavLink to="/users" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                <Shield size={15} className="nav-icon" style={{ color: 'var(--accent-red)' }} /> User Directory
              </NavLink>
            </>
          )}
        </nav>

        {/* Main */}
        <main className="main-area">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/stream" element={<StreamMonitor />} />
            <Route path="/cases/:caseId" element={<CaseDetail />} />
            <Route path="/explorer" element={<GraphExplorer />} />
            <Route path="/policy" element={<PolicyConfig />} />
            <Route path="/watchlist" element={<WatchlistManager role={role} />} />
            {isSupervisorOrCompliance && (
              <Route path="/audit" element={<AuditLedger />} />
            )}
            <Route path="/governance" element={<Governance />} />
            {isFraudAdmin && (
              <Route path="/users" element={<UserManagement />} />
            )}
          </Routes>
        </main>

        {/* Floating Toast Notification */}
        {toast && (
          <div style={{
            position: 'fixed',
            bottom: '20px',
            right: '20px',
            background: 'rgba(19, 28, 46, 0.95)',
            border: `1px solid ${toast.severity === 'HIGH' ? 'var(--accent-red)' : 'var(--accent-orange)'}`,
            borderRadius: '10px',
            padding: '16px',
            zIndex: 1000,
            maxWidth: '360px',
            boxShadow: '0 10px 30px rgba(0,0,0,0.5)',
            backdropFilter: 'blur(10px)',
            animation: 'fadeSlideIn 0.3s ease-out'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <strong style={{ color: toast.severity === 'HIGH' ? 'var(--accent-red)' : 'var(--accent-orange)', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                ⚠ {toast.title}
              </strong>
              <button onClick={() => setToast(null)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center' }}><X size={12} /></button>
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: '1.4' }}>{toast.message}</div>
          </div>
        )}
      </div>
    </BrowserRouter>
  );
}
