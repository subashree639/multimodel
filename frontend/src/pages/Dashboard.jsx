import { useState, useEffect } from 'react';
import { Container, Grid, Box, Typography, Card, CardContent, Paper, List, ListItem, ListItemText, Divider, Chip, alpha, useTheme } from '@mui/material';
import { ShoppingCart, Favorite, History, AttachMoney, TrendingUp } from '@mui/icons-material';
import { useAuth } from '../context/AuthContext';
import Loader from '../components/Loader';
import SalesChart from '../components/SalesChart';
import api from '../services/api';
import { toast } from 'react-toastify';

const Dashboard = () => {
  const { user, isAuthenticated } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const theme = useTheme();
  const userId = user?.user_id || user?.sub || '';

  useEffect(() => {
    const fetchStats = async () => {
      if (!isAuthenticated || !userId) return;
      try {
        const response = await api.get(`/admin/dashboard-stats/${userId}`);
        setStats(response.data);
      } catch (error) {
        console.error('Error fetching dashboard stats:', error);
        toast.error('Failed to load dashboard data');
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, [userId, isAuthenticated]);

  if (loading) return <Loader />;
  if (!stats) return <Typography>Failed to load dashboard</Typography>;

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Box>
            <Typography variant="h4" sx={{ fontWeight: 700 }}>Dashboard</Typography>
            <Typography color="text.secondary">Welcome back, {user?.name || 'User'}!</Typography>
          </Box>
          <Chip
            icon={<TrendingUp />}
            label={`Segment: ${stats.segment || 'General Buyer'}`}
            color="primary"
            variant="outlined"
            sx={{ fontWeight: 600 }}
          />
        </Box>

        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card elevation={0} sx={{ border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`, borderRadius: '16px' }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <ShoppingCart color="primary" sx={{ mr: 1, fontSize: 32 }} />
                  <Typography variant="h5" sx={{ fontWeight: 800 }}>{stats.totalOrders}</Typography>
                </Box>
                <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 600 }}>Total Orders</Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card elevation={0} sx={{ border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`, borderRadius: '16px' }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <Favorite color="secondary" sx={{ mr: 1, fontSize: 32 }} />
                  <Typography variant="h5" sx={{ fontWeight: 800 }}>{stats.wishlistItems}</Typography>
                </Box>
                <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 600 }}>Wishlist Items</Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card elevation={0} sx={{ border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`, borderRadius: '16px' }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <AttachMoney color="success" sx={{ mr: 1, fontSize: 32 }} />
                  <Typography variant="h5" sx={{ fontWeight: 800 }}>₹{stats.totalSpent?.toLocaleString()}</Typography>
                </Box>
                <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 600 }}>Total Spent</Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card elevation={0} sx={{ border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`, borderRadius: '16px' }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <History color="info" sx={{ mr: 1, fontSize: 32 }} />
                  <Typography variant="h5" sx={{ fontWeight: 800 }}>{stats.cartItems}</Typography>
                </Box>
                <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 600 }}>Items in Cart</Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        <Grid container spacing={3}>
          <Grid item xs={12} md={8}>
            <Paper elevation={0} sx={{ p: 3, border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`, borderRadius: '16px', height: '100%' }}>
              <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>Recent Activity</Typography>
              <Divider sx={{ mb: 2 }} />
              {stats.recentActivity?.length === 0 ? (
                <Typography color="text.secondary">No recent activity</Typography>
              ) : (
                <List sx={{ pt: 0 }}>
                  {stats.recentActivity?.map((activity, index) => (
                    <ListItem key={index} sx={{ px: 0 }}>
                      <ListItemText
                        primary={
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>
                            {activity.action === 'purchase' ? 'Purchased' : activity.action === 'add_to_cart' ? 'Added to Cart' : activity.action === 'wishlist' ? 'Added to Wishlist' : 'Viewed'} {activity.product_name}
                          </Typography>
                        }
                        secondary={new Date(activity.timestamp).toLocaleString()}
                        secondaryTypographyProps={{ fontSize: '0.8rem' }}
                      />
                    </ListItem>
                  ))}
                </List>
              )}
            </Paper>
          </Grid>

          <Grid item xs={12} md={4}>
            <Paper elevation={0} sx={{ p: 3, border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`, borderRadius: '16px', height: '100%' }}>
              <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>Your Activity Trend</Typography>
              {/* Dummy data for activity trend since we don't have time-series user activity in the backend yet */}
              <SalesChart salesData={{ labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'], revenue: [2, 5, 3, 8, 4], orders: [1, 2, 0, 3, 1] }} />
              <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: 'block', textAlign: 'center' }}>
                Activity over last 5 days
              </Typography>
            </Paper>
          </Grid>
        </Grid>
      </Box>
    </Container>
  );
};

export default Dashboard;