import { useState, useEffect } from 'react';
import { Container, Box, Typography, Grid, Paper, Button, IconButton, useTheme, alpha } from '@mui/material';
import { Delete, ShoppingCart, FavoriteBorder } from '@mui/icons-material';
import { Link as RouterLink } from 'react-router-dom';
import { toast } from 'react-toastify';
import { useAuth } from '../context/AuthContext';
import wishlistService from '../services/wishlistService';
import cartService from '../services/cartService';
import Loader from '../components/Loader';

const Wishlist = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();
  const theme = useTheme();
  const userId = user?.user_id || user?.sub || '';

  const fetchWishlist = async () => {
    if (!userId) { setLoading(false); return; }
    try {
      const data = await wishlistService.getWishlist(userId);
      setItems(data.items || []);
    } catch (error) {
      console.error('Failed to fetch wishlist:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchWishlist(); }, [userId]);

  const handleRemove = async (productId) => {
    try {
      await wishlistService.removeFromWishlist(userId, productId);
      toast.success('Removed from wishlist');
      fetchWishlist();
    } catch (error) {
      toast.error('Failed to remove');
    }
  };

  const handleMoveToCart = async (productId) => {
    try {
      await cartService.addToCart(userId, productId);
      await wishlistService.removeFromWishlist(userId, productId);
      toast.success('Moved to cart!');
      fetchWishlist();
    } catch (error) {
      toast.error('Failed to move to cart');
    }
  };

  if (loading) return <Loader />;

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 3 }}>My Wishlist</Typography>

        {items.length === 0 ? (
          <Paper sx={{ p: 6, textAlign: 'center' }}>
            <FavoriteBorder sx={{ fontSize: 80, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" color="text.secondary">Your wishlist is empty</Typography>
            <Button component={RouterLink} to="/products" variant="contained" sx={{ mt: 3 }}>
              Browse Products
            </Button>
          </Paper>
        ) : (
          <Grid container spacing={3}>
            {items.map((item, idx) => (
              <Grid item xs={12} sm={6} md={4} key={idx}>
                <Paper
                  elevation={0}
                  sx={{
                    borderRadius: '16px',
                    border: `1px solid ${alpha(theme.palette.primary.main, 0.3)}`,
                    overflow: 'hidden',
                    transition: 'all 0.3s ease',
                    '&:hover': {
                      transform: 'translateY(-4px)',
                      boxShadow: `0 12px 24px ${alpha(theme.palette.primary.main, 0.12)}`,
                    },
                  }}
                >
                  <Box sx={{ p: 2, height: 180, display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: '#fafafa' }}>
                    <Box
                      component="img"
                      src={item.product?.image_url || '/images/placeholder.png'}
                      alt={item.product?.name}
                      sx={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
                    />
                  </Box>
                  <Box sx={{ p: 2 }}>
                    <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 0.5, lineHeight: 1.3 }}>
                      {item.product?.name}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      {item.product?.category}
                    </Typography>
                    <Typography variant="h6" sx={{ fontWeight: 800, mb: 2 }}>
                      ₹{item.product?.price?.toLocaleString()}
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <Button
                        variant="contained"
                        size="small"
                        startIcon={<ShoppingCart />}
                        onClick={() => handleMoveToCart(item.product?.id)}
                        sx={{ flex: 1, borderRadius: '8px', textTransform: 'none', fontWeight: 600 }}
                      >
                        Move to Cart
                      </Button>
                      <IconButton size="small" onClick={() => handleRemove(item.product?.id)} color="error">
                        <Delete fontSize="small" />
                      </IconButton>
                    </Box>
                  </Box>
                </Paper>
              </Grid>
            ))}
          </Grid>
        )}
      </Box>
    </Container>
  );
};

export default Wishlist;
