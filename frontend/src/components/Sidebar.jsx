import { Drawer, List, ListItem, ListItemButton, ListItemIcon, ListItemText, Box, Typography, alpha, Divider, Badge } from '@mui/material';
import {
  Home, Search, Recommend, Chat, Dashboard, Assessment,
  Category, ShoppingCart, Favorite, Receipt, RateReview
} from '@mui/icons-material';
import { Link as RouterLink, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const Sidebar = ({ mobileOpen, onClose }) => {
  const location = useLocation();
  const { isAuthenticated } = useAuth();
  const drawerWidth = 260;

  const mainMenuItems = [
    { text: 'Home', icon: <Home />, path: '/' },
    { text: 'Browse Products', icon: <Search />, path: '/products' },
    { text: 'Recommendations', icon: <Recommend />, path: '/recommendations' },
    { text: 'AI Assistant', icon: <Chat />, path: '/chat' },
  ];

  const shopMenuItems = [
    { text: 'My Cart', icon: <ShoppingCart />, path: '/cart', auth: true },
    { text: 'Wishlist', icon: <Favorite />, path: '/wishlist', auth: true },
    { text: 'Orders', icon: <Receipt />, path: '/orders', auth: true },
  ];

  const insightMenuItems = [
    { text: 'Dashboard', icon: <Dashboard />, path: '/dashboard', auth: true },
    { text: 'Analytics', icon: <Assessment />, path: '/analytics' },
    { text: 'Reviews', icon: <RateReview />, path: '/reviews' },
  ];

  const renderMenuGroup = (title, items) => (
    <>
      <Typography
        variant="overline"
        sx={{
          color: alpha('#ffffff', 0.4),
          fontWeight: 700,
          letterSpacing: 2,
          px: 2,
          pt: 2,
          pb: 0.5,
          display: 'block',
        }}
      >
        {title}
      </Typography>
      <List sx={{ gap: 0.5, display: 'flex', flexDirection: 'column', px: 0 }}>
        {items
          .filter((item) => !item.auth || isAuthenticated)
          .map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <ListItem key={item.text} disablePadding>
                <ListItemButton
                  component={RouterLink}
                  to={item.path}
                  onClick={onClose}
                  sx={{
                    borderRadius: '12px',
                    mx: 1,
                    py: 1.2,
                    transition: 'all 0.3s ease',
                    backgroundColor: isActive ? alpha('#ffffff', 0.1) : 'transparent',
                    backdropFilter: isActive ? 'blur(10px)' : 'none',
                    border: isActive ? `1px solid ${alpha('#ffffff', 0.05)}` : '1px solid transparent',
                    boxShadow: isActive ? `0 8px 32px 0 ${alpha('#000000', 0.2)}` : 'none',
                    '&:hover': {
                      backgroundColor: alpha('#ffffff', 0.05),
                    },
                  }}
                >
                  <ListItemIcon
                    sx={{
                      color: isActive ? 'primary.main' : alpha('#ffffff', 0.7),
                      minWidth: 40,
                    }}
                  >
                    {item.icon}
                  </ListItemIcon>
                  <ListItemText
                    primary={item.text}
                    primaryTypographyProps={{
                      fontWeight: isActive ? 600 : 400,
                      color: isActive ? 'primary.main' : alpha('#ffffff', 0.8),
                      fontSize: '0.9rem',
                    }}
                  />
                </ListItemButton>
              </ListItem>
            );
          })}
      </List>
    </>
  );

  const drawer = (
    <Box
      sx={{
        height: '100%',
        background: 'linear-gradient(180deg, #1A1D24 0%, #111318 100%)',
        color: 'white',
        pt: 4,
        overflowY: 'auto',
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 4, px: 3 }}>
        <Category sx={{ color: 'primary.main', fontSize: 32, mr: 1.5 }} />
        <Typography variant="h6" sx={{ fontWeight: 700, letterSpacing: 1, fontFamily: '"Inter", sans-serif' }}>
          Recomora
        </Typography>
      </Box>

      {renderMenuGroup('SHOP', mainMenuItems)}
      <Divider sx={{ borderColor: alpha('#ffffff', 0.08), my: 1, mx: 2 }} />
      {renderMenuGroup('MY ACCOUNT', shopMenuItems)}
      <Divider sx={{ borderColor: alpha('#ffffff', 0.08), my: 1, mx: 2 }} />
      {renderMenuGroup('INSIGHTS', insightMenuItems)}
    </Box>
  );

  return (
    <Box component="nav" sx={{ width: { md: drawerWidth }, flexShrink: { md: 0 } }}>
      <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={onClose}
        ModalProps={{ keepMounted: true }}
        sx={{
          display: { xs: 'block', md: 'none' },
          '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth, borderRight: 'none' },
        }}
      >
        {drawer}
      </Drawer>
      <Drawer
        variant="permanent"
        sx={{
          display: { xs: 'none', md: 'block' },
          '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth, borderRight: 'none' },
        }}
        open
      >
        {drawer}
      </Drawer>
    </Box>
  );
};

export default Sidebar;