import { Box } from '@mui/material';
import { useState } from 'react';
import { useTheme } from './context/ThemeContext';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import AppRoutes from './routes/AppRoutes';

const App = () => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { darkMode } = useTheme();

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      <Sidebar mobileOpen={mobileOpen} onClose={handleDrawerToggle} />
      <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <Navbar />
        <Box component="main" sx={{ flexGrow: 1, p: 0 }}>
          <AppRoutes />
        </Box>
      </Box>
    </Box>
  );
};

export default App;