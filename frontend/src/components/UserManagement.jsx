import React, { useState, useEffect } from 'react';
import { Shield, ShieldAlert, UserCheck, UserX } from 'lucide-react';
import { api, Spinner } from './Common';

export default function UserManagement() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    api('/api/users')
      .then(setUsers)
      .catch(err => {
        console.error(err);
        setError('Failed to fetch user list. Ensure you have administrator privileges.');
      })
      .finally(() => setLoading(false));
  }, []);

  const handleToggleStatus = async (username, currentActive) => {
    if (username === localStorage.getItem('username')) {
      alert("You cannot toggle the active status of your own administrator account.");
      return;
    }
    const message = `Are you sure you want to ${currentActive ? 'Deactivate' : 'Activate'} user '${username}'?`;
    if (!window.confirm(message)) return;

    try {
      await api(`/api/users/${username}/status`, {
        method: 'PUT',
        body: JSON.stringify({ isActive: !currentActive })
      });
      // Refresh user list
      const updatedUsers = await api('/api/users');
      setUsers(updatedUsers);
    } catch (err) {
      console.error(err);
      alert('Failed to update user status.');
    }
  };

  return (
    <div className="main-content">
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <Shield size={16} className="icon" /> System User Management & Security Directory
          </div>
          <span className="stat-chip">{users.length} registered accounts</span>
        </div>
        <p style={{ color: 'var(--text-muted)', fontSize: '12px', marginBottom: '20px' }}>
          Fraud Admin Controls — Revoke, freeze, or restore investigator and compliance officer credentials across the MuleNet system.
        </p>

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

        {loading ? (
          <Spinner />
        ) : users.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', fontSize: '13px', textAlign: 'center', padding: '20px 0' }}>
            No registered users found.
          </p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-subtle)', textAlign: 'left', color: 'var(--text-muted)' }}>
                  <th style={{ padding: '10px' }}>Full Name</th>
                  <th style={{ padding: '10px' }}>Username</th>
                  <th style={{ padding: '10px' }}>Role</th>
                  <th style={{ padding: '10px' }}>Badge & Dept</th>
                  <th style={{ padding: '10px' }}>Email</th>
                  <th style={{ padding: '10px' }}>Last Active</th>
                  <th style={{ padding: '10px' }}>Status</th>
                  <th style={{ padding: '10px', textAlign: 'center' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map(user => (
                  <tr key={user.id} style={{ borderBottom: '1px solid var(--border-subtle)', verticalAlign: 'middle' }}>
                    <td style={{ padding: '10px', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {user.fullName}
                    </td>
                    <td style={{ padding: '10px', color: 'var(--text-secondary)' }}>
                      {user.username}
                    </td>
                    <td style={{ padding: '10px' }}>
                      <span style={{
                        background: 'var(--bg-elevated)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '4px',
                        padding: '2px 6px',
                        fontSize: '10px',
                        fontWeight: 600,
                        color: user.role === 'FRAUD_ADMIN' ? 'var(--accent-red)' : user.role === 'SUPERVISOR' ? 'var(--accent-orange)' : 'var(--text-secondary)'
                      }}>
                        {user.role}
                      </span>
                    </td>
                    <td style={{ padding: '10px' }}>
                      <div style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>{user.badgeNumber || '—'}</div>
                      <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{user.department || '—'}</div>
                    </td>
                    <td style={{ padding: '10px', color: 'var(--text-muted)' }}>
                      {user.email}
                    </td>
                    <td style={{ padding: '10px', color: 'var(--text-secondary)' }}>
                      {user.lastLogin ? user.lastLogin.replace('T', ' ').slice(0, 16) : 'Never'}
                    </td>
                    <td style={{ padding: '10px' }}>
                      <span style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                        background: user.isActive ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                        border: `1px solid ${user.isActive ? 'rgba(34, 197, 94, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
                        color: user.isActive ? 'var(--accent-green)' : 'var(--accent-red)',
                        borderRadius: '4px',
                        padding: '2px 6px',
                        fontSize: '10px',
                        fontWeight: 600
                      }}>
                        {user.isActive ? <><UserCheck size={10} /> Active</> : <><UserX size={10} /> Inactive</>}
                      </span>
                    </td>
                    <td style={{ padding: '10px', textAlign: 'center' }}>
                      <button
                        onClick={() => handleToggleStatus(user.username, user.isActive)}
                        disabled={user.username === localStorage.getItem('username')}
                        className="btn-analyze"
                        style={{
                          padding: '4px 10px',
                          fontSize: '11px',
                          background: 'transparent',
                          border: `1px solid ${user.isActive ? 'rgba(239, 68, 68, 0.4)' : 'rgba(34, 197, 94, 0.4)'}`,
                          color: user.isActive ? 'var(--accent-red)' : 'var(--accent-green)',
                          opacity: user.username === localStorage.getItem('username') ? 0.4 : 1,
                          cursor: user.username === localStorage.getItem('username') ? 'not-allowed' : 'pointer'
                        }}
                      >
                        {user.isActive ? 'Deactivate' : 'Activate'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
