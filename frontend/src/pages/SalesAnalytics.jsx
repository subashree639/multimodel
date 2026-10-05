import { useState, useEffect } from 'react';
import { Container, Box, Typography, Paper, Grid, Card, CardContent, Table, TableHead, TableRow, TableCell, TableBody, useTheme, alpha } from '@mui/material';
import { AttachMoney, ShoppingBag, TrendingUp, People, RateReview, Inventory } from '@mui/icons-material';
import Loader from '../components/Loader';
import SalesChart from '../components/SalesChart';
import analyticsService from '../services/analyticsService';
import { Pie } from 'react-chartjs-2';
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';

ChartJS.register(ArcElement, Tooltip, Legend);

const SalesAnalytics = () => {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const theme = useTheme();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const data = await analyticsService.getSalesAnalytics();
        setAnalytics(data);
      } catch (error) {
        console.error('Failed to fetch analytics', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) return <Loader />;
  if (!analytics) return <Typography>Failed to load analytics</Typography>;

  const sentimentData = {
    labels: Object.keys(analytics.sentimentDistribution || {}),
    datasets: [
      {
        data: Object.values(analytics.sentimentDistribution || {}),
        backgroundColor: ['#4caf50', '#ffc107', '#f44336'],
        borderWidth: 1,
      },
    ],
  };

  return (
    <Container maxWidth="xl">
      <Box sx={{ py: 4 }}>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
          Sales & Platform Analytics
        </Typography>
        <Typography color="text.secondary" sx={{ mb: 4 }}>
          Comprehensive view of platform performance
        </Typography>

        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} sm={6} md={2.4}>
            <Card elevation={0} sx={{ border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`, borderRadius: '16px' }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <AttachMoney color="primary" sx={{ mr: 1, fontSize: 32 }} />
                  <Typography variant="h5" sx={{ fontWeight: 800 }}>₹{analytics?.totalRevenue?.toLocaleString()}</Typography>
                </Box>
                <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 600 }}>Total Revenue</Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={2.4}>
            <Card elevation={0} sx={{ border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`, borderRadius: '16px' }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <ShoppingBag color="secondary" sx={{ mr: 1, fontSize: 32 }} />
                  <Typography variant="h5" sx={{ fontWeight: 800 }}>{analytics?.totalOrders}</Typography>
                </Box>
                <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 600 }}>Total Orders</Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={2.4}>
            <Card elevation={0} sx={{ border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`, borderRadius: '16px' }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <People color="success" sx={{ mr: 1, fontSize: 32 }} />
                  <Typography variant="h5" sx={{ fontWeight: 800 }}>{analytics?.totalCustomers}</Typography>
                </Box>
                <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 600 }}>Customers</Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={2.4}>
            <Card elevation={0} sx={{ border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`, borderRadius: '16px' }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <Inventory color="info" sx={{ mr: 1, fontSize: 32 }} />
                  <Typography variant="h5" sx={{ fontWeight: 800 }}>{analytics?.totalProducts}</Typography>
                </Box>
                <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 600 }}>Products</Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={2.4}>
            <Card elevation={0} sx={{ border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`, borderRadius: '16px' }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <RateReview color="warning" sx={{ mr: 1, fontSize: 32 }} />
                  <Typography variant="h5" sx={{ fontWeight: 800 }}>{analytics?.totalReviews}</Typography>
                </Box>
                <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 600 }}>Reviews</Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} md={8}>
            <Paper elevation={0} sx={{ p: 3, border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`, borderRadius: '16px', height: '100%' }}>
              <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>Revenue Trend</Typography>
              <SalesChart salesData={analytics?.chartData} />
            </Paper>
          </Grid>
          <Grid item xs={12} md={4}>
            <Paper elevation={0} sx={{ p: 3, border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`, borderRadius: '16px', height: '100%' }}>
              <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>Review Sentiment</Typography>
              <Box sx={{ height: 300, display: 'flex', justifyContent: 'center' }}>
                <Pie
                  data={sentimentData}
                  options={{
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'bottom' } }
                  }}
                />
              </Box>
            </Paper>
          </Grid>
        </Grid>

        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Paper elevation={0} sx={{ p: 3, border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`, borderRadius: '16px' }}>
              <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>Top Selling Products</Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 700 }}>Product Name</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>Category</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 700 }}>Sales/Reviews</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {analytics?.bestSellingProducts?.map((product) => (
                    <TableRow key={product.id}>
                      <TableCell>{product.name}</TableCell>
                      <TableCell><Chip label={product.category} size="small" /></TableCell>
                      <TableCell align="right" sx={{ fontWeight: 600 }}>{product.sales}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Paper>
          </Grid>
          <Grid item xs={12} md={6}>
            <Paper elevation={0} sx={{ p: 3, border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`, borderRadius: '16px' }}>
              <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>Trending Products</Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 700 }}>Product Name</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>Category</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 700 }}>Rating</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {analytics?.trendingProducts?.map((product) => (
                    <TableRow key={product.id}>
                      <TableCell>{product.name}</TableCell>
                      <TableCell><Chip label={product.category} size="small" /></TableCell>
                      <TableCell align="right" sx={{ fontWeight: 600 }}>{product.rating?.toFixed(1)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Paper>
          </Grid>
        </Grid>
      </Box>
    </Container>
  );
};

export default SalesAnalytics;