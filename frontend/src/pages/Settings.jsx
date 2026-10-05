import { Container, Box, Typography, Paper, Switch, FormControlLabel, Divider, Button } from '@mui/material';
import { useTheme } from '../context/ThemeContext';

const Settings = () => {
  const { darkMode, toggleTheme } = useTheme();

  return (
    <Container maxWidth="md">
      <Box sx={{ py: 4 }}>
        <Typography variant="h4" gutterBottom>
          Settings
        </Typography>

        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Appearance
          </Typography>
          <FormControlLabel
            control={<Switch checked={darkMode} onChange={toggleTheme} />}
            label="Dark Mode"
          />

          <Divider sx={{ my: 3 }} />

          <Typography variant="h6" gutterBottom>
            Notifications
          </Typography>
          <FormControlLabel control={<Switch defaultChecked />} label="Email Notifications" />
          <FormControlLabel control={<Switch defaultChecked />} label="Push Notifications" />

          <Divider sx={{ my: 3 }} />

          <Typography variant="h6" gutterBottom>
            Privacy
          </Typography>
          <FormControlLabel control={<Switch />} label="Make profile private" />

          <Divider sx={{ my: 3 }} />

          <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
            <Button variant="contained">Save Settings</Button>
          </Box>
        </Paper>
      </Box>
    </Container>
  );
};

export default Settings;