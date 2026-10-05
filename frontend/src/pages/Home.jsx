import { Container, Typography, Box, Button, Grid, Card, CardContent, useTheme, alpha, Chip, Rating } from '@mui/material';
import { TrendingUp, Recommend, ShoppingCart } from '@mui/icons-material';
import { Link as RouterLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { keyframes } from '@emotion/react';
import { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import cartService from '../services/cartService';
import config from '../config';

const float = keyframes`
  0% { transform: translateY(0px) rotate(0deg); }
  50% { transform: translateY(-15px) rotate(2deg); }
  100% { transform: translateY(0px) rotate(0deg); }
`;

const shimmer = keyframes`
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
`;

const Home = () => {
  const { isAuthenticated, user } = useAuth();
  const theme = useTheme();
  const [trending, setTrending] = useState([]);
  const [recommended, setRecommended] = useState([]);
  const [categories, setCategories] = useState([]);

  useEffect(() => {
    // Fetch trending products
    fetch(`${config.API_BASE_URL}/products/trending?limit=4`)
      .then((r) => r.json())
      .then((data) => setTrending(data.products || []))
      .catch(() => {});

    // Fetch categories
    fetch(`${config.API_BASE_URL}/products/categories`)
      .then((r) => r.json())
      .then((data) => setCategories((data.categories || []).slice(0, 6)))
      .catch(() => {});

    // Fetch recommendations if logged in
    if (isAuthenticated && user) {
      const userId = user.user_id || user.sub || '';
      if (userId) {
        fetch(`${config.API_BASE_URL}/recommendations/${userId}`)
          .then((r) => r.json())
          .then((data) => setRecommended((data.recommendations || []).slice(0, 4)))
          .catch(() => {});
      }
    }
  }, [isAuthenticated, user]);

  const handleAddToCart = async (productId) => {
    if (!isAuthenticated) {
      toast.info('Please login to add items to cart');
      return;
    }
    try {
      const userId = user?.user_id || user?.sub || '';
      await cartService.addToCart(userId, productId);
      toast.success('Added to cart!');
    } catch (error) {
      toast.error('Failed to add to cart');
    }
  };

  const ProductCardMini = ({ product, score, explanation }) => {
    const p = product || {};
    const displayScore = score ? Math.round(score * 100) : null;
    return (
      <Card
        elevation={0}
        sx={{
          borderRadius: '16px',
          border: `1px solid ${alpha(theme.palette.primary.main, 0.25)}`,
          transition: 'all 0.3s ease',
          height: '100%',
          cursor: 'pointer',
          position: 'relative',
          overflow: 'visible',
          '&:hover': {
            transform: 'translateY(-6px)',
            boxShadow: `0 16px 32px ${alpha(theme.palette.primary.main, 0.15)}`,
            borderColor: theme.palette.primary.main,
          },
        }}
      >
        {p.is_trending && (
          <Chip
            icon={<TrendingUp sx={{ fontSize: '14px !important' }} />}
            label="Trending"
            size="small"
            color="error"
            sx={{ position: 'absolute', top: -10, right: 10, fontWeight: 600, zIndex: 2, boxShadow: '0 4px 12px rgba(0,0,0,0.15)' }}
          />
        )}
        <Box sx={{ p: 2, display: 'flex', justifyContent: 'center', alignItems: 'center', height: 160, bgcolor: '#fafafa', borderRadius: '16px 16px 0 0' }}>
          <Box
            component="img"
            src={p.image_url || '/images/placeholder.png'}
            alt={p.name}
            sx={{ maxWidth: '90%', maxHeight: '90%', objectFit: 'contain' }}
            onError={(e) => { e.target.src = 'https://placehold.co/200x200?text=Product'; }}
          />
        </Box>
        <CardContent sx={{ pt: 1.5, pb: '12px !important' }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 700, lineHeight: 1.3, mb: 0.5, height: 36, overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
            {p.name || 'Product'}
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
            {p.category}
          </Typography>
          {p.avg_rating > 0 && (
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 0.5 }}>
              <Rating value={p.avg_rating || 0} precision={0.5} readOnly size="small" />
              <Typography variant="caption" sx={{ ml: 0.5 }}>({p.num_reviews || 0})</Typography>
            </Box>
          )}
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h6" sx={{ fontWeight: 800, color: 'text.primary' }}>
              ₹{p.price?.toLocaleString() || '0'}
            </Typography>
            {displayScore && (
              <Chip label={`${displayScore}%`} size="small" color="primary" variant="outlined" sx={{ fontWeight: 700, fontSize: '0.7rem' }} />
            )}
          </Box>
          {explanation?.why_recommended?.length > 0 && (
            <Box sx={{ mt: 1 }}>
              {explanation.why_recommended.slice(0, 2).map((reason, i) => (
                <Typography key={i} variant="caption" sx={{ display: 'block', color: 'success.main', fontSize: '0.7rem' }}>
                  ✓ {reason}
                </Typography>
              ))}
            </Box>
          )}
        </CardContent>
      </Card>
    );
  };

  return (
    <Container maxWidth="xl" disableGutters>
      {/* Hero Section */}
      <Box sx={{ pt: { xs: 4, md: 8 }, pb: { xs: 6, md: 8 }, px: { xs: 2, md: 6 } }}>
        <Grid container spacing={4} alignItems="center">
          <Grid item xs={12} md={5}>
            <Box sx={{ position: 'relative', zIndex: 2 }}>
              <Typography
                variant="h1"
                sx={{
                  fontWeight: 600,
                  fontSize: { xs: '3rem', md: '5rem' },
                  lineHeight: 1.1,
                  color: 'text.primary',
                  mb: 2,
                }}
              >
                The <Box component="span" sx={{ color: 'primary.main', fontStyle: 'italic' }}>Future</Box><br />
                of Shopping
              </Typography>
              <Typography variant="body1" sx={{ mb: 4, fontWeight: 500, color: 'text.secondary', fontSize: '1.05rem', maxWidth: 420 }}>
                AI-powered recommendations, sentiment analysis, and personalized shopping — all in one platform.
              </Typography>

              <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
                <Button
                  component={RouterLink}
                  to="/products"
                  variant="contained"
                  size="large"
                  sx={{
                    background: `linear-gradient(90deg, ${theme.palette.primary.main}, #E6C89C)`,
                    color: '#2A2D34',
                    fontWeight: 700,
                    fontSize: '1.05rem',
                    px: 4,
                    py: 1.5,
                    boxShadow: `0 12px 24px ${alpha(theme.palette.primary.main, 0.3)}`,
                    '&:hover': {
                      background: `linear-gradient(90deg, #E6C89C, ${theme.palette.primary.main})`,
                      boxShadow: `0 16px 32px ${alpha(theme.palette.primary.main, 0.4)}`,
                    },
                  }}
                >
                  Explore Now
                </Button>
                {!isAuthenticated && (
                  <Button
                    component={RouterLink}
                    to="/register"
                    variant="outlined"
                    size="large"
                    sx={{ fontWeight: 600, px: 4, py: 1.5 }}
                  >
                    Sign Up Free
                  </Button>
                )}
              </Box>
            </Box>
          </Grid>

          <Grid item xs={12} md={7} sx={{ position: 'relative' }}>
            <Box sx={{ width: '100%', height: 350, position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Box
                sx={{
                  position: 'absolute',
                  width: '85%',
                  height: 220,
                  borderRadius: '24px',
                  background: alpha(theme.palette.primary.main, 0.08),
                  backdropFilter: 'blur(20px)',
                  border: `1px solid ${alpha(theme.palette.primary.main, 0.15)}`,
                  boxShadow: `0 30px 60px ${alpha('#000000', 0.08)}`,
                }}
              />
              {/* Feature badges */}
              {[
                { label: '🤖 AI Recommendations', top: 20, left: 30, delay: '0s' },
                { label: '📊 Sentiment Analysis', top: -10, right: 40, delay: '1s' },
                { label: '🔥 Trending Detection', bottom: 10, left: 100, delay: '2s' },
              ].map((badge, i) => (
                <Chip
                  key={i}
                  label={badge.label}
                  sx={{
                    position: 'absolute',
                    ...badge,
                    animation: `${float} 6s ease-in-out infinite`,
                    animationDelay: badge.delay,
                    zIndex: 2,
                    fontWeight: 600,
                    bgcolor: 'background.paper',
                    boxShadow: `0 8px 24px ${alpha('#000', 0.1)}`,
                    border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`,
                    fontSize: '0.85rem',
                    py: 2.5,
                  }}
                />
              ))}
            </Box>
          </Grid>
        </Grid>
      </Box>

      {/* Trending Products */}
      {trending.length > 0 && (
        <Box sx={{ px: { xs: 2, md: 6 }, pb: 6 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
            <Box>
              <Typography variant="h4" sx={{ fontWeight: 800, fontFamily: '"Inter", sans-serif' }}>
                🔥 Trending Now
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Most popular products right now
              </Typography>
            </Box>
            <Button component={RouterLink} to="/products" variant="outlined" size="small">
              View All
            </Button>
          </Box>
          <Grid container spacing={2.5}>
            {trending.map((product, idx) => (
              <Grid item xs={6} sm={6} md={3} key={product.id || idx}>
                <Box component={RouterLink} to={`/product/${product.id}`} sx={{ textDecoration: 'none' }}>
                  <ProductCardMini product={{ ...product, is_trending: true }} />
                </Box>
              </Grid>
            ))}
          </Grid>
        </Box>
      )}

      {/* Recommended For You (only when logged in) */}
      {isAuthenticated && recommended.length > 0 && (
        <Box sx={{ px: { xs: 2, md: 6 }, pb: 6 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
            <Box>
              <Typography variant="h4" sx={{ fontWeight: 800, fontFamily: '"Inter", sans-serif' }}>
                ✨ Recommended For You
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Personalized picks based on your behavior
              </Typography>
            </Box>
            <Button component={RouterLink} to="/recommendations" variant="outlined" size="small">
              See More
            </Button>
          </Box>
          <Grid container spacing={2.5}>
            {recommended.map((rec, idx) => (
              <Grid item xs={6} sm={6} md={3} key={rec.product?.id || idx}>
                <Box component={RouterLink} to={`/product/${rec.product?.id}`} sx={{ textDecoration: 'none' }}>
                  <ProductCardMini product={rec.product} score={rec.score} explanation={rec.explanation} />
                </Box>
              </Grid>
            ))}
          </Grid>
        </Box>
      )}

      {/* Categories */}
      {categories.length > 0 && (
        <Box sx={{ px: { xs: 2, md: 6 }, pb: 8 }}>
          <Typography variant="h4" sx={{ fontWeight: 800, mb: 3, fontFamily: '"Inter", sans-serif' }}>
            📦 Top Categories
          </Typography>
          <Grid container spacing={2}>
            {categories.map((cat, idx) => (
              <Grid item xs={6} sm={4} md={2} key={idx}>
                <Button
                  component={RouterLink}
                  to={`/products?category=${encodeURIComponent(cat)}`}
                  fullWidth
                  sx={{
                    py: 3,
                    borderRadius: '16px',
                    border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`,
                    bgcolor: alpha(theme.palette.primary.main, 0.04),
                    textTransform: 'capitalize',
                    fontWeight: 600,
                    color: 'text.primary',
                    '&:hover': {
                      bgcolor: alpha(theme.palette.primary.main, 0.1),
                      borderColor: theme.palette.primary.main,
                      transform: 'translateY(-2px)',
                    },
                    transition: 'all 0.3s ease',
                  }}
                >
                  {cat}
                </Button>
              </Grid>
            ))}
          </Grid>
        </Box>
      )}
    </Container>
  );
};

export default Home;