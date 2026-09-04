import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#5b8def',
      light: '#7eb3ff',
      dark: '#3b6fd4',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#a855f7',
      light: '#c084fc',
      dark: '#7e22ce',
      contrastText: '#ffffff',
    },
    error: {
      main: '#ef4444',
      light: '#f87171',
      dark: '#dc2626',
    },
    warning: {
      main: '#f97316',
      light: '#fb923c',
      dark: '#ea580c',
    },
    info: {
      main: '#06b6d4',
      light: '#22d3ee',
      dark: '#0891b2',
    },
    success: {
      main: '#22c55e',
      light: '#4ade80',
      dark: '#16a34a',
    },
    background: {
      default: '#06090f',
      paper: '#0f1626',
    },
    text: {
      primary: '#f1f5f9',
      secondary: '#94a3b8',
      disabled: '#64748b',
    },
    divider: 'rgba(91, 141, 239, 0.12)',
    action: {
      hover: 'rgba(91, 141, 239, 0.08)',
      selected: 'rgba(91, 141, 239, 0.16)',
      disabled: 'rgba(255, 255, 255, 0.3)',
      disabledBackground: 'rgba(255, 255, 255, 0.12)',
    },
  },
  typography: {
    fontFamily: "'Inter', sans-serif",
    allVariants: {
      color: '#f1f5f9',
    },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        html: {
          backgroundColor: '#06090f',
          color: '#f1f5f9',
        },
        body: {
          backgroundColor: '#06090f',
          color: '#f1f5f9',
          scrollbarColor: 'rgba(91, 141, 239, 0.25) #06090f',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          backgroundColor: '#0f1626',
          color: '#f1f5f9',
          border: '1px solid rgba(91, 141, 239, 0.12)',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          backgroundColor: '#0f1626',
          color: '#f1f5f9',
          border: '1px solid rgba(91, 141, 239, 0.12)',
        },
      },
    },
    MuiTypography: {
      styleOverrides: {
        root: {
          color: '#f1f5f9',
        },
        colorTextSecondary: {
          color: '#94a3b8 !important',
        },
      },
    },
    MuiInputBase: {
      styleOverrides: {
        root: {
          color: '#f1f5f9',
        },
        input: {
          color: '#f1f5f9',
          '&::placeholder': {
            color: '#8197b0',
            opacity: 1,
          },
        },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        notchedOutline: {
          borderColor: 'rgba(91, 141, 239, 0.2)',
        },
        root: {
          '&:hover .MuiOutlinedInput-notchedOutline': {
            borderColor: 'rgba(91, 141, 239, 0.45)',
          },
          '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
            borderColor: '#5b8def',
          },
        },
      },
    },
    MuiInputLabel: {
      styleOverrides: {
        root: {
          color: '#94a3b8',
          '&.Mui-focused': {
            color: '#5b8def',
          },
        },
      },
    },
    MuiSelect: {
      styleOverrides: {
        icon: {
          color: '#94a3b8',
        },
      },
    },
    MuiMenuItem: {
      styleOverrides: {
        root: {
          color: '#f1f5f9',
          '&:hover': {
            backgroundColor: 'rgba(91, 141, 239, 0.12)',
          },
          '&.Mui-selected': {
            backgroundColor: 'rgba(91, 141, 239, 0.2)',
          },
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          color: '#f1f5f9',
          borderBottom: '1px solid rgba(91, 141, 239, 0.1)',
        },
        head: {
          color: '#94a3b8',
          fontWeight: 700,
        },
      },
    },
    MuiDivider: {
      styleOverrides: {
        root: {
          borderColor: 'rgba(91, 141, 239, 0.12)',
        },
      },
    },
  },
});

export default theme;
