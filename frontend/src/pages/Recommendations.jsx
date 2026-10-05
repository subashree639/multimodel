import { useState, useEffect } from 'react';
import { Container, Grid, Box, Typography, Tabs, Tab, Chip, Paper, alpha, useTheme } from '@mui/material';
import { Recommend, TrendingUp, GroupWork } from '@mui/icons-material';
import RecommendationCard from '../components/RecommendationCard';
import Loader from '../components/Loader';
import { useAuth } from '../context/AuthContext';
import config from '../config';

const Recommendations = () => {
  const [recommendations, setRecommendations] = useState([]);
  const [trending, setTrending] = useState([]);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState(0);
  const [userSegment, setUserSegment] = useState('');
  const { user, isAuthenticated } = useAuth();
  const theme = useTheme();

  useEffect(() => {
    const fetchRecommendations = async () => {
      setLoading(true);
      try {
        const userId = user?.user_id || user?.sub || user?.id || 'test@example.com';

        const response = await fetch(`${config.API_BASE_URL}/recommendations/${userId}`);
        if (!response.ok) throw new Error('Network response was not ok');
        const data = await response.json();

        const recs = data.recommendations?.map((r) => ({
          id: r.product.id,
          product_id: r.product.id,
          name: r.product.name,
          price: r.product.price,
          score: r.score,
          reason: r.explanation?.reason || 'Recommended for you',
          explanation: r.explanation,
          image_url: r.product.image_url || '/images/placeholder.png',
          is_trending: r.explanation?.is_trending || false,
        })) || [];

        const trends = data.trending?.map((p) => ({
          id: p.id,
          product_id: p.id,
          name: p.name,
          price: p.price,
          score: 0.95,
          is_trending: true,
          image_url: p.image_url || '/images/placeholder.png',
        })) || [];

        setRecommendations(recs);
        setTrending(trends);
        setUserSegment(data.user_segment || '');
      } catch (error) {
        console.error('Failed to fetch recommendations:', error);
        setRecommendations([]);
        setTrending([]);
      } finally {
        setLoading(false);
      }
    };

    fetchRecommendations();
  }, [user]);

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
          <Typography variant="h4" sx={{ fontWeight: 700 }}>
            Product Recommendations
          </Typography>
          {userSegment && (
            <Chip
              icon={<GroupWork />}
              label={`Segment: ${userSegment}`}
              size="small"
              color="primary"
              variant="outlined"
              sx={{ fontWeight: 600 }}
            />
          )}
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          AI-powered picks using SVD, TF-IDF Similarity, Sentiment Analysis, and Sales Trends
        </Typography>

        <Tabs value={tab} onChange={(e, v) => setTab(v)} sx={{ mb: 3 }}>
          <Tab icon={<Recommend sx={{ fontSize: 18 }} />} iconPosition="start" label="For You" />
          <Tab icon={<TrendingUp sx={{ fontSize: 18 }} />} iconPosition="start" label="Trending" />
        </Tabs>

        {loading ? (
          <Loader />
        ) : (
          <>
            {tab === 0 && (
              <>
                {recommendations.length === 0 ? (
                  <Paper sx={{ p: 6, textAlign: 'center' }}>
                    <Recommend sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                    <Typography variant="h6" color="text.secondary">
                      {isAuthenticated ? 'Building your recommendations...' : 'Log in to get personalized recommendations'}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                      Browse and interact with products to improve your recommendations
                    </Typography>
                  </Paper>
                ) : (
                  <>
                    {/* Formula Explanation */}
                    <Paper sx={{ p: 2, mb: 3, borderRadius: '12px', bgcolor: alpha(theme.palette.primary.main, 0.04), border: `1px solid ${alpha(theme.palette.primary.main, 0.1)}` }}>
                      <Typography variant="body2" sx={{ fontWeight: 600, color: 'text.secondary' }}>
                        📊 Score = <Chip label="40% SVD" size="small" sx={{ mx: 0.3, fontWeight: 700 }} /> +
                        <Chip label="25% Similarity" size="small" sx={{ mx: 0.3, fontWeight: 700 }} /> +
                        <Chip label="20% Sentiment" size="small" sx={{ mx: 0.3, fontWeight: 700 }} /> +
                        <Chip label="15% Sales Trend" size="small" sx={{ mx: 0.3, fontWeight: 700 }} />
                      </Typography>
                    </Paper>
                    <Grid container spacing={3}>
                      {recommendations.map((rec) => (
                        <Grid item xs={12} sm={6} md={4} key={rec.id}>
                          <RecommendationCard recommendation={rec} />
                        </Grid>
                      ))}
                    </Grid>
                  </>
                )}
              </>
            )}

            {tab === 1 && (
              <>
                {trending.length === 0 ? (
                  <Paper sx={{ p: 6, textAlign: 'center' }}>
                    <TrendingUp sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                    <Typography variant="h6" color="text.secondary">No trending products yet</Typography>
                  </Paper>
                ) : (
                  <Grid container spacing={3}>
                    {trending.map((rec) => (
                      <Grid item xs={12} sm={6} md={4} key={rec.id}>
                        <RecommendationCard recommendation={rec} />
                      </Grid>
                    ))}
                  </Grid>
                )}
              </>
            )}
          </>
        )}
      </Box>
    </Container>
  );
};

export default Recommendations;