import { useState, useEffect } from 'react';
import {
  Container, Box, Typography, Paper, Button, IconButton,
  Table, TableHead, TableRow, TableCell, TableBody,
  Avatar, Chip, Divider, useTheme, alpha
} from '@mui/material';
import { Delete, ShoppingBag, ArrowBack } from '@mui/icons-material';
import { Link as RouterLink } from 'react-router-dom';
import { toast } from 'react-toastify';
import { useAuth } from '../context/AuthContext';
import cartService from '../services/cartService';
import Loader from '../components/Loader';

const Cart = () => {
  const [cart, setCart] = useState({ items: [], total: 0 });
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();
  const theme = useTheme();

  const userId = user?.user_id || user?.sub || '';

  const fetchCart = async () => {
    if (!userId) { setLoading(false); return; }
    try {
      const data = await cartService.getCart(userId);
      setCart(data);
    } catch (error) {
      console.error('Failed to fetch cart:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchCart(); }, [userId]);

  const handleRemove = async (productId) => {
    try {
      await cartService.removeFromCart(userId, productId);
      toast.success('Removed from cart');
      fetchCart();
    } catch (error) {
      toast.error('Failed to remove item');
    }
  };

  const handleCheckout = async () => {
    try {
      const result = await cartService.checkout(userId);
      toast.success(`Order placed! Total: ₹${result.total}`);
      setCart({ items: [], total: 0 });
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Checkout failed');
    }
  };

  if (loading) return <Loader />;

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
          <Button component={RouterLink} to="/products" startIcon={<ArrowBack />} sx={{ mr: 2 }}>
            Continue Shopping
          </Button>
          <Typography variant="h4" sx={{ fontWeight: 700 }}>Shopping Cart</Typography>
          <Chip label={`${cart.items.length} items`} sx={{ ml: 2 }} />
        </Box>

        {cart.items.length === 0 ? (
          <Paper sx={{ p: 6, textAlign: 'center' }}>
            <ShoppingBag sx={{ fontSize: 80, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" color="text.secondary">Your cart is empty</Typography>
            <Button component={RouterLink} to="/products" variant="contained" sx={{ mt: 3 }}>
              Browse Products
            </Button>
          </Paper>
        ) : (
          <Box sx={{ display: 'flex', gap: 3, flexDirection: { xs: 'column', md: 'row' } }}>
            <Paper sx={{ flexGrow: 1, overflow: 'hidden' }}>
              <Table>
                <TableHead>
                  <TableRow sx={{ bgcolor: alpha(theme.palette.primary.main, 0.05) }}>
                    <TableCell>Product</TableCell>
                    <TableCell align="center">Qty</TableCell>
                    <TableCell align="right">Subtotal</TableCell>
                    <TableCell align="center" width={60}></TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {cart.items.map((item, idx) => (
                    <TableRow key={idx} hover>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                          <Avatar
                            variant="rounded"
                            src={item.product?.image_url}
                            sx={{ width: 56, height: 56 }}
                          />
                          <Box>
                            <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                              {item.product?.name}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {item.product?.category} · ₹{item.product?.price?.toLocaleString()}
                            </Typography>
                          </Box>
                        </Box>
                      </TableCell>
                      <TableCell align="center">
                        <Chip label={item.quantity} size="small" />
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                          ₹{item.subtotal?.toLocaleString()}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <IconButton size="small" onClick={() => handleRemove(item.product?.id)} color="error">
                          <Delete fontSize="small" />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Paper>

            <Paper sx={{ width: { xs: '100%', md: 320 }, p: 3, height: 'fit-content' }}>
              <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>Order Summary</Typography>
              <Divider sx={{ mb: 2 }} />
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography color="text.secondary">Subtotal</Typography>
                <Typography sx={{ fontWeight: 600 }}>₹{cart.total?.toLocaleString()}</Typography>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography color="text.secondary">Shipping</Typography>
                <Typography sx={{ fontWeight: 600, color: 'success.main' }}>Free</Typography>
              </Box>
              <Divider sx={{ my: 2 }} />
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
                <Typography variant="h6" sx={{ fontWeight: 700 }}>Total</Typography>
                <Typography variant="h6" sx={{ fontWeight: 700, color: 'primary.main' }}>
                  ₹{cart.total?.toLocaleString()}
                </Typography>
              </Box>
              <Button
                fullWidth
                variant="contained"
                size="large"
                onClick={handleCheckout}
                sx={{
                  background: `linear-gradient(90deg, ${theme.palette.primary.main}, #E6C89C)`,
                  color: '#2A2D34',
                  fontWeight: 700,
                  py: 1.5,
                }}
              >
                Place Order
              </Button>
            </Paper>
          </Box>
        )}
      </Box>
    </Container>
  );
};

export default Cart;
