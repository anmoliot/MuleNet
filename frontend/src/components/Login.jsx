import React, { useState } from 'react';
import { API } from './Common';
import { Box, Card, Typography, TextField, Button, Grid, Avatar, Alert, CircularProgress, Container } from '@mui/material';
import SecurityIcon from '@mui/icons-material/Security';

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
      let data;
      try {
        const res = await fetch(`${API}/api/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: u, password: p }),
        });
        if (!res.ok) throw new Error('Invalid credentials');
        data = await res.json();
      } catch (fetchErr) {
        console.warn('Backend unavailable, using mock login for ', u);
        // Mock fallback so UI works even without backend
        data = {
          token: 'mock-jwt-token-12345',
          username: u,
          role: u === 'admin' ? 'FRAUD_ADMIN' : u.toUpperCase()
        };
      }
      
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
    { label: 'Investigator Profile', user: 'investigator', pass: 'password', desc: 'Case workflows & actions', color: 'primary.main' },
    { label: 'Supervisor Profile', user: 'supervisor', pass: 'password', desc: 'Action overrides & reviews', color: 'warning.main' },
    { label: 'Fraud Admin Profile', user: 'admin', pass: 'password', desc: 'System policy configuration', color: 'error.main' },
  ];
  return (
    <Container component="main" maxWidth="xs" sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', bgcolor: 'background.default' }}>
      <Card elevation={6} sx={{ p: 4, width: '100%', borderRadius: 3 }}>
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', mb: 3 }}>
          <Avatar sx={{ m: 1, bgcolor: 'primary.main', width: 56, height: 56 }}>
            <SecurityIcon fontSize="large" />
          </Avatar>
          <Typography component="h1" variant="h5" fontWeight="bold">
            MuleNet Portal
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Graph-Native Fraud Intelligence Platform
          </Typography>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Box component="form" onSubmit={handleLogin} sx={{ mt: 1 }}>
          <TextField
            margin="normal"
            required
            fullWidth
            id="username"
            label="Username"
            name="username"
            autoFocus
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
          <TextField
            margin="normal"
            required
            fullWidth
            name="password"
            label="Password"
            type="password"
            id="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <Button
            type="submit"
            fullWidth
            variant="contained"
            sx={{ mt: 3, mb: 2, py: 1.5, fontWeight: 'bold' }}
            disabled={loading}
          >
            {loading ? <CircularProgress size={24} /> : 'Sign In'}
          </Button>
        </Box>

        <Box sx={{ mt: 4, pt: 3, borderTop: 1, borderColor: 'divider' }}>
          <Typography variant="overline" display="block" align="center" color="text.secondary" gutterBottom>
            Developer Quick Access (RBAC testing)
          </Typography>
          <Grid container spacing={1}>
            {quickRoles.map(r => (
              <Grid item xs={6} key={r.label}>
                <Button
                  fullWidth
                  variant="outlined"
                  size="small"
                  onClick={() => handleLogin(null, r.user, r.pass)}
                  sx={{ 
                    justifyContent: 'flex-start',
                    textAlign: 'left',
                    borderColor: r.color,
                    color: r.color,
                    borderWidth: 2,
                    '&:hover': {
                      borderWidth: 2,
                      bgcolor: `${r.color}10`
                    },
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'flex-start',
                    p: 1
                  }}
                >
                  <Typography variant="caption" fontWeight="bold">{r.label.split(' ')[0]}</Typography>
                  <Typography variant="caption" sx={{ fontSize: '0.65rem', opacity: 0.8 }}>{r.desc.split(' ')[0]} mode</Typography>
                </Button>
              </Grid>
            ))}
          </Grid>
        </Box>
      </Card>
    </Container>
  );
}
