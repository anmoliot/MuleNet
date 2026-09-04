import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Zap, FileText, ChevronRight, Download } from 'lucide-react';
import { api, RiskBadge, StatusBadge, Spinner } from './Common';
import { testIntakeRequest } from '../testData';
import { Box, Card, CardContent, Typography, Button, TextField, Select, MenuItem, Slider, Grid, IconButton, Tooltip, Paper } from '@mui/material';

export default function Dashboard() {
  const [cases, setCases] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');
  const [minRisk, setMinRisk] = useState(0);
  const navigate = useNavigate();

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (searchQuery) params.append('query', searchQuery);
      if (statusFilter) params.append('status', statusFilter);
      if (severityFilter) params.append('severityLevel', severityFilter);
      if (minRisk > 0) params.append('minRisk', minRisk);

      const [c, s] = await Promise.all([
        api(`/api/cases?${params.toString()}`),
        api('/api/cases/stats/summary'),
      ]);
      setCases(c);
      setStats(s);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [searchQuery, statusFilter, severityFilter, minRisk]);

  useEffect(() => { loadData(); }, [loadData]);

  const runAnalysis = async () => {
    setLoading(true);
    try {
      const result = await api('/api/intake', {
        method: 'POST',
        body: JSON.stringify(testIntakeRequest),
      });
      await loadData();
      if (result.caseId) navigate(`/cases/${result.caseId}`);
    } catch (e) {
      console.error(e);
      setLoading(false);
    }
  };

  const handleExportCSV = () => {
    const token = localStorage.getItem('token');
    const API_BASE = import.meta.env?.VITE_BACKEND_API_URL || 'http://localhost:8080';
    fetch(`${API_BASE}/api/cases/export/csv`, {
      headers: {
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      }
    })
    .then(res => {
      if (!res.ok) throw new Error("Failed to export");
      return res.blob();
    })
    .then(blob => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `cases_export_${Date.now()}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    })
    .catch(err => {
      console.error(err);
      alert("Failed to export cases CSV (ensure backend is running)");
    });
  };

  const userRole = localStorage.getItem('role');
  const canExport = ['SUPERVISOR', 'COMPLIANCE_OFFICER', 'FRAUD_ADMIN'].includes(userRole);

  const StatCard = ({ label, value, sub, color }) => (
    <Card elevation={2} sx={{ height: '100%' }}>
      <CardContent>
        <Typography color="text.secondary" gutterBottom variant="subtitle2">
          {label}
        </Typography>
        <Typography variant="h4" component="div" sx={{ color: color, fontWeight: 'bold' }}>
          {value}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {sub}
        </Typography>
      </CardContent>
    </Card>
  );

  return (
    <Box sx={{ flexGrow: 1, p: 3, maxWidth: 1200, margin: '0 auto' }}>
      <Typography variant="h4" gutterBottom fontWeight="bold" color="text.primary">
        Command Center
      </Typography>

      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard label="Active Cases" value={stats.active_cases ?? '—'} sub="Open + Investigating" color="warning.main" />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard label="Critical Alerts" value={stats.critical_alerts ?? '—'} sub="Score > 80" color="error.main" />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard label="Frozen Accounts" value={stats.frozen_accounts ?? '—'} sub="Freeze executed" color="info.main" />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard label="Avg Risk Score" value={stats.avg_risk_score ?? '—'} sub="Across all cases" color="success.main" />
        </Grid>
      </Grid>

      <Paper elevation={1} sx={{ p: 2, mb: 4, display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
        <TextField
          size="small"
          placeholder="Search Case ID..."
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          InputProps={{
            startAdornment: <Search size={20} style={{ marginRight: 8, color: '#999' }} />,
          }}
          sx={{ flex: 1, minWidth: 200 }}
        />
        <Select
          size="small"
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
          displayEmpty
          sx={{ minWidth: 150 }}
        >
          <MenuItem value="">All Statuses</MenuItem>
          <MenuItem value="OPEN">Open</MenuItem>
          <MenuItem value="INVESTIGATING">Investigating</MenuItem>
          <MenuItem value="ESCALATED">Escalated</MenuItem>
          <MenuItem value="FROZEN">Frozen</MenuItem>
          <MenuItem value="CLOSED">Closed</MenuItem>
          <MenuItem value="DISMISSED">Dismissed</MenuItem>
        </Select>
        <Select
          size="small"
          value={severityFilter}
          onChange={e => setSeverityFilter(e.target.value)}
          displayEmpty
          sx={{ minWidth: 150 }}
        >
          <MenuItem value="">All Severities</MenuItem>
          <MenuItem value="CRITICAL">Critical</MenuItem>
          <MenuItem value="HIGH">High</MenuItem>
          <MenuItem value="MEDIUM">Medium</MenuItem>
          <MenuItem value="LOW">Low</MenuItem>
        </Select>
        <Box sx={{ display: 'flex', alignItems: 'center', minWidth: 200, px: 2 }}>
          <Typography variant="body2" color="text.primary" sx={{ mr: 2, whiteSpace: 'nowrap' }}>Min Risk: {minRisk}%</Typography>
          <Slider
            value={minRisk}
            onChange={(e, val) => setMinRisk(val)}
            step={5}
            min={0}
            max={100}
            size="small"
          />
        </Box>
      </Paper>

      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Card elevation={3} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom display="flex" alignItems="center" gap={1} color="text.primary">
                <Zap size={20} /> Quick Analysis
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Submit the test complaint through the full 11-layer pipeline: Data Ingestion → Trust Fabric → Risk Mesh → Knowledge Graph → XGBoost → GNN → Risk Fusion → Policy Engine → Recovery Intelligence
              </Typography>
              <Button 
                variant="contained" 
                color="primary" 
                fullWidth 
                onClick={runAnalysis} 
                disabled={loading}
                startIcon={<Zap size={16} />}
              >
                {loading ? 'Analyzing…' : 'Run Intake Analysis'}
              </Button>
              {loading && <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}><Spinner /></Box>}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={8}>
          <Card elevation={3} sx={{ height: '100%' }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" display="flex" alignItems="center" gap={1} color="text.primary">
                  <FileText size={20} /> Case Queue
                </Typography>
                <Box display="flex" alignItems="center" gap={2}>
                  <Typography variant="body2" fontWeight="bold" color="text.primary">{cases.length} total</Typography>
                  {canExport && (
                    <Button variant="outlined" size="small" startIcon={<Download size={16} />} onClick={handleExportCSV}>
                      Export CSV
                    </Button>
                  )}
                </Box>
              </Box>
              
              {cases.length === 0 ? (
                <Typography color="text.secondary" align="center" sx={{ py: 4 }}>
                  No cases yet. Run an analysis to create your first case.
                </Typography>
              ) : (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  {cases.map((c, i) => (
                    <Paper 
                      key={c.caseId || c.id} 
                      elevation={1} 
                      sx={{ 
                        p: 2, 
                        display: 'flex', 
                        alignItems: 'center', 
                        justifyContent: 'space-between', 
                        cursor: 'pointer',
                        bgcolor: 'rgba(15, 22, 38, 0.6)',
                        border: '1px solid rgba(91, 141, 239, 0.12)',
                        '&:hover': { bgcolor: 'rgba(91, 141, 239, 0.08)', borderColor: 'rgba(91, 141, 239, 0.25)' }
                      }}
                      onClick={() => navigate(`/cases/${c.caseId || c.id}`)}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <Typography variant="body2" color="text.secondary">#{i + 1}</Typography>
                        <Typography variant="body1" fontWeight="bold" color="text.primary">{c.caseId || c.id}</Typography>
                        <Typography variant="body2" color="text.secondary">{c.complaintId || c.title}</Typography>
                      </Box>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <StatusBadge status={c.status} />
                        <Typography variant="body1" fontWeight="bold" color="error.main">
                          {c.riskScore?.toFixed(1)}
                        </Typography>
                        <ChevronRight size={20} color="#94a3b8" />
                      </Box>
                    </Paper>
                  ))}
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}

