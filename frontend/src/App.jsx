import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, NavLink, useNavigate } from 'react-router-dom';
import {
  ShieldAlert, Activity, Network, BarChart3, Settings, Shield, Bell, X, Store, FileText, AlertTriangle, Menu as MenuIcon
} from 'lucide-react';
import {
  Box, Drawer, AppBar, Toolbar, List, Typography, Divider, IconButton, ListItem, ListItemButton, ListItemIcon, ListItemText, Badge, Avatar, Menu, MenuItem, Alert
} from '@mui/material';

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
import MerchantRiskOverview from './components/MerchantRiskOverview';
import MetricsDashboard from './components/MetricsDashboard';
import AuditTrailViewer from './components/AuditTrailViewer';
import FailureDemo from './components/FailureDemo';
import { API } from './components/Common';

const drawerWidth = 260;

function MainLayout({ children, username, role, alerts, handleLogout }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [anchorEl, setAnchorEl] = useState(null);

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const isSupervisorOrCompliance = role === 'SUPERVISOR' || role === 'COMPLIANCE_OFFICER';
  const isFraudAdmin = role === 'FRAUD_ADMIN';

  const navItems = [
    { label: 'Intelligence', isHeader: true },
    { label: 'Dashboard', path: '/', icon: <Activity size={20} /> },
    { label: 'Stream Monitor', path: '/stream', icon: <Activity size={20} color="#06b6d4" /> },
    { label: 'Graph Explorer', path: '/explorer', icon: <Network size={20} /> },
    { label: 'Watchlist Registry', path: '/watchlist', icon: <Shield size={20} color="#f97316" /> },
    
    { label: 'Merchant Demo', isHeader: true },
    { label: 'Merchant Overview', path: '/merchant-risk', icon: <Store size={20} color="#22c55e" /> },
    { label: 'Metrics Dashboard', path: '/metrics-dashboard', icon: <BarChart3 size={20} /> },
    { label: 'Audit Trail', path: '/audit-trail', icon: <FileText size={20} color="#06b6d4" /> },
    { label: 'Failure Demo', path: '/failure-demo', icon: <AlertTriangle size={20} color="#ef4444" /> },

    { label: 'Operations', isHeader: true },
    { label: 'Policy Config', path: '/policy', icon: <Settings size={20} /> },
    ...(isSupervisorOrCompliance ? [{ label: 'Audit Ledger', path: '/audit', icon: <ShieldAlert size={20} /> }] : []),
    { label: 'Governance', path: '/governance', icon: <BarChart3 size={20} /> },

    ...(isFraudAdmin ? [
      { label: 'Administration', isHeader: true },
      { label: 'User Directory', path: '/users', icon: <Shield size={20} color="#ef4444" /> }
    ] : [])
  ];

  const drawer = (
    <div>
      <Toolbar sx={{ display: 'flex', alignItems: 'center', gap: 2, px: 2, py: 1 }}>
        <Avatar sx={{ bgcolor: 'primary.main', width: 32, height: 32 }}>🛡</Avatar>
        <Box>
          <Typography variant="subtitle1" fontWeight="bold">MuleNet</Typography>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: -0.5 }}>Fraud Intelligence</Typography>
        </Box>
      </Toolbar>
      <Divider />
      <List sx={{ px: 1 }}>
        {navItems.map((item, index) => {
          if (item.isHeader) {
            return (
              <Typography key={index} variant="overline" color="text.secondary" sx={{ px: 2, display: 'block', mt: 2, mb: 1, fontWeight: 'bold' }}>
                {item.label}
              </Typography>
            );
          }
          return (
            <ListItem key={item.label} disablePadding sx={{ mb: 0.5 }}>
              <ListItemButton 
                component={NavLink} 
                to={item.path}
                style={({ isActive }) => ({
                  borderRadius: 8,
                  backgroundColor: isActive ? 'rgba(59, 130, 246, 0.08)' : 'transparent',
                  color: isActive ? '#3b82f6' : 'inherit'
                })}
              >
                <ListItemIcon sx={{ minWidth: 40, color: 'inherit' }}>
                  {item.icon}
                </ListItemIcon>
                <ListItemText primary={item.label} primaryTypographyProps={{ fontSize: '0.875rem', fontWeight: 500 }} />
              </ListItemButton>
            </ListItem>
          );
        })}
      </List>
    </div>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      <AppBar
        position="fixed"
        sx={{
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          ml: { sm: `${drawerWidth}px` },
          bgcolor: 'background.paper',
          color: 'text.primary',
          boxShadow: 1
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Box sx={{ flexGrow: 1 }} />
          <IconButton color="inherit" onClick={(e) => setAnchorEl(e.currentTarget)}>
            <Badge badgeContent={alerts.length} color="error">
              <Bell size={20} />
            </Badge>
          </IconButton>
          <Menu
            anchorEl={anchorEl}
            open={Boolean(anchorEl)}
            onClose={() => setAnchorEl(null)}
            PaperProps={{ sx: { width: 320, maxHeight: 400 } }}
          >
            <Box sx={{ px: 2, py: 1, borderBottom: 1, borderColor: 'divider' }}>
              <Typography variant="subtitle2" fontWeight="bold">Live Notifications</Typography>
            </Box>
            {alerts.length === 0 ? (
              <MenuItem disabled>No new notifications</MenuItem>
            ) : (
              alerts.map((a, i) => (
                <MenuItem key={i} sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}>
                  <Typography variant="body2" color={a.severity === 'HIGH' ? 'error.main' : 'warning.main'} fontWeight="bold">
                    {a.title}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" noWrap sx={{ width: '100%' }}>
                    {a.message}
                  </Typography>
                </MenuItem>
              ))
            )}
          </Menu>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, ml: 3 }}>
            <Box sx={{ textAlign: 'right', display: { xs: 'none', md: 'block' } }}>
              <Typography variant="body2" fontWeight="bold">{username}</Typography>
              <Typography variant="caption" color="text.secondary">{role}</Typography>
            </Box>
            <Button variant="outlined" size="small" onClick={handleLogout}>Sign Out</Button>
          </Box>
        </Toolbar>
      </AppBar>
      <Box component="nav" sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}>
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }}
          sx={{ display: { xs: 'block', sm: 'none' }, '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth } }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{ display: { xs: 'none', sm: 'block' }, '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth } }}
          open
        >
          {drawer}
        </Drawer>
      </Box>
      <Box component="main" sx={{ flexGrow: 1, p: 3, width: { sm: `calc(100% - ${drawerWidth}px)` }, mt: 8 }}>
        {children}
      </Box>
    </Box>
  );
}

// Ensure Button is imported at the top
import { Button } from '@mui/material';

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [username, setUsername] = useState(localStorage.getItem('username'));
  const [role, setRole] = useState(localStorage.getItem('role'));
  const [alerts, setAlerts] = useState([]);
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
      <MainLayout username={username} role={role} alerts={alerts} handleLogout={handleLogout}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/stream" element={<StreamMonitor />} />
          <Route path="/cases/:caseId" element={<CaseDetail />} />
          <Route path="/explorer" element={<GraphExplorer />} />
          <Route path="/policy" element={<PolicyConfig />} />
          <Route path="/watchlist" element={<WatchlistManager role={role} />} />
          <Route path="/merchant-risk" element={<MerchantRiskOverview />} />
          <Route path="/metrics-dashboard" element={<MetricsDashboard />} />
          <Route path="/audit-trail" element={<AuditTrailViewer />} />
          <Route path="/failure-demo" element={<FailureDemo />} />
          {isSupervisorOrCompliance && (
            <Route path="/audit" element={<AuditLedger />} />
          )}
          <Route path="/governance" element={<Governance />} />
          {isFraudAdmin && (
            <Route path="/users" element={<UserManagement />} />
          )}
        </Routes>

        {toast && (
          <Box sx={{ position: 'fixed', bottom: 24, right: 24, zIndex: 9999 }}>
            <Alert 
              severity={toast.severity === 'HIGH' ? 'error' : 'warning'}
              onClose={() => setToast(null)}
              sx={{ boxShadow: 3 }}
            >
              <Typography variant="subtitle2">{toast.title}</Typography>
              <Typography variant="body2">{toast.message}</Typography>
            </Alert>
          </Box>
        )}
      </MainLayout>
    </BrowserRouter>
  );
}
