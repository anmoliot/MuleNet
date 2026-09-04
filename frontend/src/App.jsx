import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, NavLink, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ShieldAlert, Activity, Network, BarChart3, Settings, Shield, Bell, Store, FileText, AlertTriangle, Menu as MenuIcon
} from 'lucide-react';
import {
  Box, Drawer, AppBar, Toolbar, List, Typography, Divider, IconButton, ListItem,
  ListItemButton, ListItemIcon, ListItemText, Badge, Menu, MenuItem, Alert, Button
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
import AnimatedLogo from './components/AnimatedLogo';
import Footer from './components/Footer';
import { API } from './components/Common';

const drawerWidth = 260;

/* ─── Page transition wrapper ─── */
function PageWrapper({ children }) {
  const location = useLocation();
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={location.pathname}
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        transition={{ duration: 0.28, ease: 'easeOut' }}
        style={{ flex: 1, display: 'flex', flexDirection: 'column' }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}

/* ─── Notification toast ─── */
function LiveToast({ toast, onClose }) {
  if (!toast) return null;
  return (
    <AnimatePresence>
      <motion.div
        key={toast.title}
        initial={{ opacity: 0, x: 80, scale: 0.9 }}
        animate={{ opacity: 1, x: 0, scale: 1 }}
        exit={{ opacity: 0, x: 80, scale: 0.9 }}
        transition={{ type: 'spring', stiffness: 350, damping: 28 }}
        style={{ position: 'fixed', bottom: 28, right: 28, zIndex: 9999, maxWidth: 360 }}
      >
        <Alert
          severity={toast.severity === 'HIGH' ? 'error' : 'warning'}
          onClose={onClose}
          sx={{
            boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
            border: '1px solid',
            borderColor: toast.severity === 'HIGH' ? 'error.dark' : 'warning.dark',
            borderRadius: 2,
            backdropFilter: 'blur(12px)',
          }}
        >
          <Typography variant="subtitle2" fontWeight="bold">{toast.title}</Typography>
          <Typography variant="body2">{toast.message}</Typography>
        </Alert>
      </motion.div>
    </AnimatePresence>
  );
}

/* ─── Main layout ─── */
function MainLayout({ children, username, role, alerts, handleLogout }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [anchorEl, setAnchorEl] = useState(null);

  const isSupervisorOrCompliance = role === 'SUPERVISOR' || role === 'COMPLIANCE_OFFICER';
  const isFraudAdmin = role === 'FRAUD_ADMIN';

  const navItems = [
    { label: 'Intelligence', isHeader: true },
    { label: 'Dashboard',        path: '/',                icon: <Activity size={18} /> },
    { label: 'Stream Monitor',   path: '/stream',          icon: <Activity size={18} color="#06b6d4" /> },
    { label: 'Graph Explorer',   path: '/explorer',        icon: <Network size={18} /> },
    { label: 'Watchlist',        path: '/watchlist',       icon: <Shield size={18} color="#f97316" /> },

    { label: 'Merchant Demo', isHeader: true },
    { label: 'Merchant Overview',path: '/merchant-risk',   icon: <Store size={18} color="#22c55e" /> },
    { label: 'Metrics',          path: '/metrics-dashboard',icon: <BarChart3 size={18} /> },
    { label: 'Audit Trail',      path: '/audit-trail',     icon: <FileText size={18} color="#06b6d4" /> },
    { label: 'Failure Demo',     path: '/failure-demo',    icon: <AlertTriangle size={18} color="#ef4444" /> },

    { label: 'Operations', isHeader: true },
    { label: 'Policy Config',    path: '/policy',          icon: <Settings size={18} /> },
    ...(isSupervisorOrCompliance ? [{ label: 'Audit Ledger', path: '/audit', icon: <ShieldAlert size={18} /> }] : []),
    { label: 'Governance',       path: '/governance',      icon: <BarChart3 size={18} /> },

    ...(isFraudAdmin ? [
      { label: 'Administration', isHeader: true },
      { label: 'User Directory', path: '/users',           icon: <Shield size={18} color="#ef4444" /> },
    ] : []),
  ];

  const drawer = (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Brand */}
      <Toolbar sx={{ px: 2, py: 1.5 }}>
        <AnimatedLogo size={36} showText />
      </Toolbar>
      <Divider sx={{ borderColor: 'rgba(91,141,239,0.1)' }} />

      {/* Nav */}
      <List sx={{ px: 1, flex: 1 }}>
        {navItems.map((item, idx) => {
          if (item.isHeader) {
            return (
              <Typography key={idx} variant="overline" sx={{
                px: 1.5, display: 'block', mt: 2, mb: 0.5,
                fontSize: '0.62rem', fontWeight: 800, letterSpacing: '1.8px',
                color: 'var(--text-muted)',
              }}>
                {item.label}
              </Typography>
            );
          }
          return (
            <ListItem key={item.label} disablePadding sx={{ mb: 0.25 }}>
              <ListItemButton
                component={NavLink}
                to={item.path}
                onClick={() => setMobileOpen(false)}
                style={({ isActive }) => ({
                  borderRadius: 8,
                  border: '1px solid',
                  borderColor: isActive ? 'rgba(91,141,239,0.22)' : 'transparent',
                  backgroundColor: isActive ? 'rgba(91,141,239,0.12)' : 'transparent',
                  color: isActive ? '#5b8def' : '#94a3b8',
                  transition: 'all 0.18s cubic-bezier(0.4,0,0.2,1)',
                })}
                sx={{
                  py: 0.9, px: 1.5,
                  '&:hover': {
                    backgroundColor: 'rgba(91,141,239,0.07)',
                    color: '#f1f5f9',
                    borderColor: 'rgba(91,141,239,0.12)',
                  },
                }}
              >
                <ListItemIcon sx={{ minWidth: 34, color: 'inherit', opacity: 0.85 }}>
                  {item.icon}
                </ListItemIcon>
                <ListItemText
                  primary={item.label}
                  primaryTypographyProps={{ fontSize: '0.82rem', fontWeight: 500 }}
                />
              </ListItemButton>
            </ListItem>
          );
        })}
      </List>

      {/* User pill at bottom */}
      <Box sx={{
        m: 1.5, p: 1.5,
        background: 'rgba(91,141,239,0.06)',
        border: '1px solid rgba(91,141,239,0.12)',
        borderRadius: 2,
      }}>
        <Typography variant="body2" fontWeight="bold" sx={{ color: '#f1f5f9', fontSize: '0.8rem' }}>
          {username}
        </Typography>
        <Typography variant="caption" sx={{ color: 'var(--text-secondary)', fontSize: '0.68rem', letterSpacing: '1px', textTransform: 'uppercase' }}>
          {role}
        </Typography>
      </Box>
    </div>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: '#06090f' }}>
      {/* ── AppBar ── */}
      <AppBar
        position="fixed"
        elevation={0}
        sx={{
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          ml: { sm: `${drawerWidth}px` },
          bgcolor: 'rgba(10,15,28,0.85)',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          borderBottom: '1px solid rgba(91,141,239,0.1)',
          boxShadow: '0 1px 0 rgba(91,141,239,0.06), 0 4px 24px rgba(0,0,0,0.3)',
          color: '#f1f5f9',
        }}
      >
        <Toolbar sx={{ gap: 1.5 }}>
          <IconButton color="inherit" edge="start" onClick={() => setMobileOpen(!mobileOpen)} sx={{ display: { sm: 'none' } }}>
            <MenuIcon />
          </IconButton>

          {/* Animated "LIVE" pill */}
          <motion.div
            animate={{ opacity: [1, 0.5, 1] }}
            transition={{ duration: 2, repeat: Infinity }}
            style={{
              display: 'flex', alignItems: 'center', gap: 5,
              background: 'rgba(34,197,94,0.08)',
              border: '1px solid rgba(34,197,94,0.25)',
              borderRadius: 20, padding: '3px 11px',
              fontSize: 9, fontWeight: 700, color: '#22c55e',
              letterSpacing: '1.5px', textTransform: 'uppercase',
            }}
          >
            <span style={{
              width: 5, height: 5, borderRadius: '50%',
              background: '#22c55e', boxShadow: '0 0 6px #22c55e',
              display: 'inline-block',
            }} />
            LIVE
          </motion.div>

          <Box sx={{ flexGrow: 1 }} />

          {/* Alerts bell */}
          <IconButton
            color="inherit"
            onClick={(e) => setAnchorEl(e.currentTarget)}
            sx={{
              position: 'relative',
              '&:hover': { background: 'rgba(91,141,239,0.1)' },
            }}
          >
            <motion.div whileHover={{ rotate: [0, -15, 15, -10, 10, 0] }} transition={{ duration: 0.5 }}>
              <Badge badgeContent={alerts.length} color="error">
                <Bell size={19} />
              </Badge>
            </motion.div>
          </IconButton>

          <Menu
            anchorEl={anchorEl}
            open={Boolean(anchorEl)}
            onClose={() => setAnchorEl(null)}
            PaperProps={{
              sx: {
                width: 320, maxHeight: 400,
                bgcolor: '#0a0f1c',
                border: '1px solid rgba(91,141,239,0.15)',
                boxShadow: '0 8px 40px rgba(0,0,0,0.6)',
              },
            }}
          >
            <Box sx={{ px: 2, py: 1, borderBottom: '1px solid rgba(91,141,239,0.1)' }}>
              <Typography variant="subtitle2" fontWeight="bold" sx={{ color: '#f1f5f9' }}>
                Live Notifications
              </Typography>
            </Box>
            {alerts.length === 0 ? (
              <MenuItem disabled sx={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>No new notifications</MenuItem>
            ) : (
              alerts.map((a, i) => (
                <MenuItem key={i} sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', borderBottom: '1px solid rgba(91,141,239,0.06)' }}>
                  <Typography variant="body2" color={a.severity === 'HIGH' ? 'error.main' : 'warning.main'} fontWeight="bold">
                    {a.title}
                  </Typography>
                  <Typography variant="caption" color="var(--text-secondary)" noWrap sx={{ width: '100%' }}>
                    {a.message}
                  </Typography>
                </MenuItem>
              ))
            )}
          </Menu>

          {/* Sign out */}
          <motion.div whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.96 }}>
            <Button
              variant="outlined"
              size="small"
              onClick={handleLogout}
              sx={{
                borderColor: 'rgba(91,141,239,0.3)',
                color: '#5b8def',
                fontSize: '0.72rem',
                letterSpacing: '0.5px',
                '&:hover': {
                  borderColor: '#5b8def',
                  background: 'rgba(91,141,239,0.1)',
                },
              }}
            >
              Sign Out
            </Button>
          </motion.div>
        </Toolbar>
      </AppBar>

      {/* ── Drawer ── */}
      <Box component="nav" sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}>
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={() => setMobileOpen(false)}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': {
              width: drawerWidth,
              bgcolor: 'rgba(10,15,28,0.97)',
              borderRight: '1px solid rgba(91,141,239,0.1)',
              backdropFilter: 'blur(20px)',
            },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': {
              width: drawerWidth,
              bgcolor: 'rgba(10,15,28,0.97)',
              borderRight: '1px solid rgba(91,141,239,0.1)',
              backdropFilter: 'blur(20px)',
            },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>

      {/* ── Main content ── */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          display: 'flex',
          flexDirection: 'column',
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          mt: '64px',
          minHeight: 'calc(100vh - 64px)',
          bgcolor: '#06090f',
        }}
      >
        <Box sx={{ flex: 1, p: 3 }}>
          {children}
        </Box>
        <Footer />
      </Box>
    </Box>
  );
}

/* ─── Root App ─── */
export default function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [username, setUsername] = useState(localStorage.getItem('username'));
  const [role, setRole] = useState(localStorage.getItem('role'));
  const [alerts, setAlerts] = useState([]);
  const [toast, setToast] = useState(null);

  useEffect(() => {
    if (!token) return;
    const url = `${API}/api/notifications/subscribe?token=${token}`;
    const es = new EventSource(url);
    es.addEventListener('alert', (e) => {
      try {
        const data = JSON.parse(e.data);
        setAlerts((prev) => [data, ...prev.slice(0, 9)]);
        setToast(data);
        setTimeout(() => setToast(null), 6000);
      } catch (err) {
        console.error('SSE parse error:', err);
      }
    });
    es.onerror = (err) => console.error('SSE error:', err);
    return () => es.close();
  }, [token]);

  const handleLoginSuccess = (t, u, r) => {
    setToken(t); setUsername(u); setRole(r);
  };
  const handleLogout = () => {
    ['token', 'username', 'role'].forEach((k) => localStorage.removeItem(k));
    setToken(null); setUsername(null); setRole(null);
  };

  if (!token) return <Login onLoginSuccess={handleLoginSuccess} />;

  const isSupervisorOrCompliance = role === 'SUPERVISOR' || role === 'COMPLIANCE_OFFICER';
  const isFraudAdmin = role === 'FRAUD_ADMIN';

  return (
    <BrowserRouter>
      <MainLayout username={username} role={role} alerts={alerts} handleLogout={handleLogout}>
        <PageWrapper>
          <Routes>
            <Route path="/"               element={<Dashboard />} />
            <Route path="/stream"         element={<StreamMonitor />} />
            <Route path="/cases/:caseId"  element={<CaseDetail />} />
            <Route path="/explorer"       element={<GraphExplorer />} />
            <Route path="/policy"         element={<PolicyConfig />} />
            <Route path="/watchlist"      element={<WatchlistManager role={role} />} />
            <Route path="/merchant-risk"  element={<MerchantRiskOverview />} />
            <Route path="/metrics-dashboard" element={<MetricsDashboard />} />
            <Route path="/audit-trail"    element={<AuditTrailViewer />} />
            <Route path="/failure-demo"   element={<FailureDemo />} />
            <Route path="/governance"     element={<Governance />} />
            {isSupervisorOrCompliance && <Route path="/audit" element={<AuditLedger />} />}
            {isFraudAdmin && <Route path="/users" element={<UserManagement />} />}
          </Routes>
        </PageWrapper>
      </MainLayout>

      <LiveToast toast={toast} onClose={() => setToast(null)} />
    </BrowserRouter>
  );
}
