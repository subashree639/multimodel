import { AppBar, Toolbar, Typography, IconButton, Box, Button, Badge, useTheme as useMuiTheme } from '@mui/material';
import { DarkMode, LightMode, Person, ShoppingCart } from '@mui/icons-material';
import { Link as RouterLink, useLocation } from 'react-router-dom';
import { useTheme } from '../context/ThemeContext';
import { useAuth } from '../context/AuthContext';

const Navbar = () => {
  const { darkMode, toggleTheme } = useTheme();
  const muiTheme = useMuiTheme();
  const { user, logout, isAuthenticated } = useAuth();
  const location = useLocation();

  const navItems = [
    { text: 'HOME', path: '/' },
    { text: 'PRODUCTS', path: '/products' },
    { text: 'RECOMMENDATIONS', path: '/recommendations' },
    { text: 'AI ASSISTANT', path: '/chat' },
  ];

  return (
    <AppBar
      position="sticky"
      elevation={0}
      sx={{
        backgroundColor: 'transparent',
        borderBottom: 'none',
        pt: 2,
        pb: 1,
        color: muiTheme.palette.text.primary,
      }}
    >
      <Toolbar sx={{ justifyContent: 'flex-end', px: { xs: 2, md: 4 } }}>
        <Box sx={{ flexGrow: 1 }} />

        <Box sx={{ display: { xs: 'none', md: 'flex' }, gap: 3, alignItems: 'center' }}>
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <Button
                key={item.text}
                component={RouterLink}
                to={item.path}
                sx={{
                  color: isActive ? 'primary.main' : 'text.primary',
                  fontWeight: 600,
                  fontSize: '0.85rem',
                  letterSpacing: 1,
                  position: 'relative',
                  '&::after': {
                    content: '""',
                    position: 'absolute',
                    bottom: 0,
                    left: 0,
                    width: isActive ? '100%' : '0%',
                    height: '2px',
                    backgroundColor: 'primary.main',
                    transition: 'width 0.3s ease',
                  },
                  '&:hover::after': {
                    width: '100%',
                  },
                  '&:hover': {
                    backgroundColor: 'transparent',
                    color: 'primary.main',
                  },
                }}
              >
                {item.text}
              </Button>
            );
          })}

          {isAuthenticated && (
            <Button
              component={RouterLink}
              to="/dashboard"
              sx={{
                color: location.pathname === '/dashboard' ? 'primary.main' : 'text.primary',
                fontWeight: 600,
                fontSize: '0.85rem',
                letterSpacing: 1,
              }}
            >
              DASHBOARD
            </Button>
          )}

          {isAuthenticated && (
            <IconButton
              component={RouterLink}
              to="/cart"
              color="inherit"
              sx={{ mx: 0.5 }}
            >
              <ShoppingCart fontSize="small" />
            </IconButton>
          )}

          <IconButton color="inherit" onClick={toggleTheme} sx={{ mx: 0.5 }}>
            {darkMode ? <LightMode fontSize="small" /> : <DarkMode fontSize="small" />}
          </IconButton>

          {isAuthenticated ? (
            <>
              <IconButton color="inherit" component={RouterLink} to="/profile" size="small">
                <Person fontSize="small" />
              </IconButton>
              <Button color="inherit" onClick={logout} sx={{ fontWeight: 600, fontSize: '0.85rem', letterSpacing: 1 }}>
                LOGOUT
              </Button>
            </>
          ) : (
            <Button component={RouterLink} to="/login" color="inherit" sx={{ fontWeight: 600, fontSize: '0.85rem', letterSpacing: 1 }}>
              LOGIN
            </Button>
          )}
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Navbar;