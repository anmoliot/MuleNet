import React, { useState } from 'react';
import { API } from './Common';

export default function Login({ onLoginSuccess }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e, quickUser, quickPass) => {
    if (e) e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const u = quickUser || username;
      const p = quickPass || password;
      const res = await fetch(`${API}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: u, password: p }),
      });
      if (!res.ok) {
        throw new Error('Invalid credentials');
      }
      const data = await res.json();
      localStorage.setItem('token', data.token);
      localStorage.setItem('username', data.username);
      localStorage.setItem('role', data.role);
      onLoginSuccess(data.token, data.username, data.role);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const quickRoles = [
    { label: 'Investigator Profile', user: 'investigator', pass: 'password', desc: 'Case workflows & actions', color: 'var(--accent-primary)' },
    { label: 'Supervisor Profile', user: 'supervisor', pass: 'password', desc: 'Action overrides & reviews', color: 'var(--accent-orange)' },
    { label: 'Fraud Admin Profile', user: 'admin', pass: 'password', desc: 'System policy configuration', color: 'var(--accent-red)' },
    { label: 'Compliance Officer', user: 'compliance', pass: 'password', desc: 'Audit ledger & governance', color: 'var(--accent-cyan)' }
  ];

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      background: '#070b14',
      fontFamily: "'Inter', sans-serif",
      color: 'var(--text-primary)',
      padding: '20px'
    }}>
      <div style={{
        width: '100%',
        maxWidth: '480px',
        background: 'rgba(17, 24, 39, 0.7)',
        backdropFilter: 'blur(16px)',
        border: '1px solid rgba(99, 122, 180, 0.2)',
        borderRadius: '16px',
        padding: '40px',
        boxShadow: '0 20px 40px rgba(0,0,0,0.5)'
      }}>
        <div style={{ textAlign: 'center', marginBottom: '30px' }}>
          <div style={{
            width: '60px',
            height: '60px',
            background: 'rgba(59, 130, 246, 0.1)',
            border: '2px solid var(--accent-primary)',
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '28px',
            margin: '0 auto 15px auto',
            boxShadow: '0 0 20px rgba(59,130,246,0.2)'
          }}>🛡</div>
          <h2 style={{ fontSize: '20px', fontWeight: 800, margin: 0, letterSpacing: '-0.5px' }}>MuleNet Portal</h2>
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '5px' }}>Graph-Native Fraud Intelligence Platform</p>
        </div>

        {error && (
          <div style={{
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid var(--border-danger)',
            color: 'var(--accent-red)',
            borderRadius: '8px',
            padding: '12px',
            fontSize: '12px',
            marginBottom: '20px'
          }}>
            ⚠️ {error}
          </div>
        )}

        <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)' }}>Username</label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder="Enter username"
              required
              style={{
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                padding: '10px 14px',
                color: 'var(--text-primary)',
                fontSize: '13px',
                outline: 'none'
              }}
            />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)' }}>Password</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="Enter password"
              required
              style={{
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                padding: '10px 14px',
                color: 'var(--text-primary)',
                fontSize: '13px',
                outline: 'none'
              }}
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            style={{
              background: 'var(--accent-primary)',
              color: '#fff',
              border: 'none',
              borderRadius: '8px',
              padding: '12px',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
              marginTop: '8px',
              transition: 'background 0.2s'
            }}
          >
            {loading ? 'Authenticating...' : 'Sign In'}
          </button>
        </form>

        <div style={{ marginTop: '30px', borderTop: '1px solid var(--border-subtle)', paddingTop: '20px' }}>
          <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '1px', textTransform: 'uppercase', marginBottom: '12px', textAlign: 'center' }}>
            Developer Quick Access (RBAC testing)
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            {quickRoles.map(r => (
              <button
                key={r.label}
                onClick={() => handleLogin(null, r.user, r.pass)}
                style={{
                  background: 'rgba(255,255,255,0.02)',
                  border: '1px solid var(--border-subtle)',
                  borderLeft: `3px solid ${r.color}`,
                  borderRadius: '6px',
                  padding: '8px',
                  textAlign: 'left',
                  cursor: 'pointer',
                  outline: 'none'
                }}
              >
                <div style={{ fontSize: '11px', fontWeight: 700, color: r.color }}>{r.label.split(' ')[0]}</div>
                <div style={{ fontSize: '9px', color: 'var(--text-muted)', marginTop: '2px' }}>{r.desc.split(' ')[0]} mode</div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
