import { useState, useEffect } from 'react';
import {
  Container, Box, Typography, Paper, Chip, Table, TableHead,
  TableRow, TableCell, TableBody, Collapse, IconButton, useTheme, alpha
} from '@mui/material';
import { ExpandMore, ExpandLess, Receipt } from '@mui/icons-material';
import { useAuth } from '../context/AuthContext';
import orderService from '../services/orderService';
import Loader from '../components/Loader';

const OrderRow = ({ order }) => {
  const [open, setOpen] = useState(false);
  const theme = useTheme();

  return (
    <>
      <TableRow hover sx={{ cursor: 'pointer' }} onClick={() => setOpen(!open)}>
        <TableCell>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            #{order.id?.slice(-8).toUpperCase()}
          </Typography>
        </TableCell>
        <TableCell>{order.items?.length || 0} items</TableCell>
        <TableCell>
          <Typography sx={{ fontWeight: 700 }}>₹{order.total?.toLocaleString()}</Typography>
        </TableCell>
        <TableCell>
          <Chip
            label={order.status || 'completed'}
            size="small"
            color={order.status === 'completed' ? 'success' : 'warning'}
            sx={{ fontWeight: 600, textTransform: 'capitalize' }}
          />
        </TableCell>
        <TableCell>
          {order.created_at ? new Date(order.created_at).toLocaleDateString() : 'N/A'}
        </TableCell>
        <TableCell>
          <IconButton size="small">{open ? <ExpandLess /> : <ExpandMore />}</IconButton>
        </TableCell>
      </TableRow>
      <TableRow>
        <TableCell colSpan={6} sx={{ py: 0 }}>
          <Collapse in={open} timeout="auto" unmountOnExit>
            <Box sx={{ p: 2, bgcolor: alpha(theme.palette.primary.main, 0.03), borderRadius: 2, my: 1 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>Order Items</Typography>
              {order.items?.map((item, idx) => (
                <Box key={idx} sx={{ display: 'flex', justifyContent: 'space-between', py: 0.5 }}>
                  <Typography variant="body2">{item.name} × {item.quantity}</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>₹{item.subtotal?.toLocaleString()}</Typography>
                </Box>
              ))}
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </>
  );
};

const Orders = () => {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();
  const theme = useTheme();
  const userId = user?.user_id || user?.sub || '';

  useEffect(() => {
    const fetchOrders = async () => {
      if (!userId) { setLoading(false); return; }
      try {
        const data = await orderService.getOrders(userId);
        setOrders(data.orders || []);
      } catch (error) {
        console.error('Failed to fetch orders:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchOrders();
  }, [userId]);

  if (loading) return <Loader />;

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 3 }}>Order History</Typography>

        {orders.length === 0 ? (
          <Paper sx={{ p: 6, textAlign: 'center' }}>
            <Receipt sx={{ fontSize: 80, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" color="text.secondary">No orders yet</Typography>
          </Paper>
        ) : (
          <Paper sx={{ overflow: 'hidden' }}>
            <Table>
              <TableHead>
                <TableRow sx={{ bgcolor: alpha(theme.palette.primary.main, 0.05) }}>
                  <TableCell sx={{ fontWeight: 700 }}>Order ID</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Items</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Total</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Status</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Date</TableCell>
                  <TableCell></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {orders.map((order) => (
                  <OrderRow key={order.id} order={order} />
                ))}
              </TableBody>
            </Table>
          </Paper>
        )}
      </Box>
    </Container>
  );
};

export default Orders;
