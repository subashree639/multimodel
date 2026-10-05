import { CircularProgress, Box } from '@mui/material';

const Loader = ({ size = 40 }) => {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', py: 4 }}>
      <CircularProgress size={size} />
    </Box>
  );
};

export default Loader;