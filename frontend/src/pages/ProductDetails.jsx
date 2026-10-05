import { useState, useEffect } from 'react';
import {
  Container, Grid, Box, Typography, Rating, Button, Chip, Paper, Divider,
  useTheme, alpha, Card, CardContent, LinearProgress
} from '@mui/material';
import { ShoppingCart, Favorite, Share, TrendingUp, CheckCircle } from '@mui/icons-material';
import { useParams, Link as RouterLink } from 'react-router-dom';
import { toast } from 'react-toastify';
import { useAuth } from '../context/AuthContext';
import cartService from '../services/cartService';
import wishlistService from '../services/wishlistService';
import Loader from '../components/Loader';
import ReviewChart from '../components/ReviewChart';
import config from '../config';

const ProductDetails = () => {
  const { id } = useParams();
  const [product, setProduct] = useState(null);
  const [similar, setSimilar] = useState([]);
  const [frequentlyBought, setFrequentlyBought] = useState([]);
  const [recommended, setRecommended] = useState([]);
  const [whyThis, setWhyThis] = useState([]);
  const [loading, setLoading] = useState(true);
  const { user, isAuthenticated } = useAuth();
  const theme = useTheme();

  useEffect(() => {
    const fetchProduct = async () => {
      setLoading(true);
      try {
        const res = await fetch(`${config.API_BASE_URL}/products/${id}`);
        if (!res.ok) throw new Error('Failed');
        const data = await res.json();
        setProduct(data);
      } catch (error) {
        console.error('Failed to fetch product:', error);
        setProduct({
          id,
          name: 'Product',
          category: 'General',
          price: 0,
          description: 'Product details unavailable.',
          features: [],
          avg_rating: 0,
          num_reviews: 0,
          sentiment: { positive: 33, neutral: 34, negative: 33 },
        });
      } finally {
        setLoading(false);
      }
    };

    const fetchSimilar = async () => {
      try {
        const res = await fetch(`${config.API_BASE_URL}/recommendations/similar/${id}`);
        if (res.ok) {
          const data = await res.json();
          setSimilar(data.similar_products || []);
        }
      } catch (e) { console.error(e); }
    };

    const fetchFrequentlyBought = async () => {
      try {
        const res = await fetch(`${config.API_BASE_URL}/recommendations/frequently-bought-together/${id}`);
        if (res.ok) {
          const data = await res.json();
          setFrequentlyBought(data.frequently_bought_together || []);
        }
      } catch (e) { console.error(e); }
    };

    const fetchRecommended = async () => {
      try {
        const uid = user?.user_id || user?.sub || 'guest';
        const res = await fetch(`${config.API_BASE_URL}/recommendations/${uid}?top_n=5`);
        if (res.ok) {
          const data = await res.json();
          const recs = (data.recommendations || []).filter((r) => r.product?.id !== id).slice(0, 5);
          setRecommended(recs);
          const mine = (data.recommendations || []).find((r) => r.product?.id === id);
          if (mine?.explanation) {
            setWhyThis(mine.explanation.reasons || mine.explanation.why_recommended || []);
          }
        }
      } catch (e) { console.error(e); }
    };

    fetchProduct();
    fetchSimilar();
    fetchFrequentlyBought();
    fetchRecommended();
  }, [id]);

  const handleAddToCart = async () => {
    if (!isAuthenticated) { toast.info('Please login first'); return; }
    try {
      const userId = user?.user_id || user?.sub || '';
      await cartService.addToCart(userId, id);
      toast.success('Added to cart!');
    } catch (error) {
      toast.error('Failed to add to cart');
    }
  };

  const handleWishlist = async () => {
    if (!isAuthenticated) { toast.info('Please login first'); return; }
    try {
      const userId = user?.user_id || user?.sub || '';
      await wishlistService.addToWishlist(userId, id);
      toast.success('Added to wishlist!');
    } catch (error) {
      toast.error('Failed to add to wishlist');
    }
  };

  if (loading) return <Loader />;
  if (!product) return <Typography>Product not found</Typography>;

  const sentiment = product.sentiment || { positive: 33, neutral: 34, negative: 33 };
  // Convert to percentage if values are 0-1
  const sentPos = sentiment.positive > 1 ? sentiment.positive : Math.round(sentiment.positive * 100);
  const sentNeg = sentiment.negative > 1 ? sentiment.negative : Math.round(sentiment.negative * 100);
  const sentNeu = sentiment.neutral > 1 ? sentiment.neutral : Math.round(sentiment.neutral * 100);

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        <Grid container spacing={4}>
          {/* Product Image */}
          <Grid item xs={12} md={5}>
            <Paper
              elevation={0}
              sx={{
                p: 3,
                borderRadius: '20px',
                border: `1px solid ${alpha(theme.palette.primary.main, 0.15)}`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                minHeight: 400,
                bgcolor: '#fafafa',
                position: 'relative',
              }}
            >
              {product.is_trending && (
                <Chip
                  icon={<TrendingUp />}
                  label="Trending"
                  color="error"
                  sx={{ position: 'absolute', top: 16, left: 16, fontWeight: 600 }}
                />
              )}
              <Box
                component="img"
                src={product.image_url || 'https://placehold.co/400x400?text=Product'}
                alt={product.name}
                sx={{ maxWidth: '100%', maxHeight: 350, objectFit: 'contain' }}
                onError={(e) => { e.target.src = 'https://placehold.co/400x400?text=Product'; }}
              />
            </Paper>
          </Grid>

          {/* Product Info */}
          <Grid item xs={12} md={7}>
            <Chip label={product.category} color="primary" size="small" sx={{ mb: 1.5, fontWeight: 600 }} />
            <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>{product.name}</Typography>

            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <Rating value={product.avg_rating || 0} precision={0.5} readOnly />
              <Typography sx={{ ml: 1, fontWeight: 600 }}>
                {product.avg_rating?.toFixed(1)} ({product.num_reviews || product.review_count || 0} reviews)
              </Typography>
            </Box>

            <Typography variant="h4" color="primary" sx={{ mb: 2, fontWeight: 800 }}>
              ₹{product.price?.toLocaleString()}
            </Typography>

            <Typography variant="body1" sx={{ mb: 3, color: 'text.secondary', lineHeight: 1.7 }}>
              {product.description}
            </Typography>

            {product.features?.length > 0 && (
              <>
                <Typography variant="h6" sx={{ fontWeight: 700, mb: 1 }}>Features</Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 3 }}>
                  {product.features.map((feature, index) => (
                    <Chip key={index} label={feature} variant="outlined" size="small" />
                  ))}
                </Box>
              </>
            )}

            <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
              <Button
                variant="contained"
                size="large"
                startIcon={<ShoppingCart />}
                onClick={handleAddToCart}
                sx={{
                  background: `linear-gradient(90deg, ${theme.palette.primary.main}, #E6C89C)`,
                  color: '#2A2D34',
                  fontWeight: 700,
                  px: 4,
                }}
              >
                Add to Cart
              </Button>
              <Button variant="outlined" startIcon={<Favorite />} onClick={handleWishlist}>
                Wishlist
              </Button>
            </Box>

            {/* Sentiment Summary */}
            <Paper sx={{ p: 2.5, borderRadius: '16px', bgcolor: alpha(theme.palette.primary.main, 0.03) }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1.5 }}>
                Review Sentiment
              </Typography>
              {[
                { label: 'Positive', value: sentPos, color: '#4caf50' },
                { label: 'Neutral', value: sentNeu, color: '#ffc107' },
                { label: 'Negative', value: sentNeg, color: '#f44336' },
              ].map((s) => (
                <Box key={s.label} sx={{ mb: 1 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.3 }}>
                    <Typography variant="caption" sx={{ fontWeight: 600 }}>{s.label}</Typography>
                    <Typography variant="caption" sx={{ fontWeight: 700 }}>{s.value}%</Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={s.value}
                    sx={{
                      height: 8,
                      borderRadius: 4,
                      bgcolor: alpha(s.color, 0.15),
                      '& .MuiLinearProgress-bar': { bgcolor: s.color, borderRadius: 4 },
                    }}
                  />
                </Box>
              ))}
            </Paper>
          </Grid>
        </Grid>

        {/* Similar Products */}
        {similar.length > 0 && (
          <Box sx={{ mt: 6 }}>
            <Typography variant="h5" sx={{ fontWeight: 700, mb: 3 }}>Similar Products</Typography>
            <Grid container spacing={2}>
              {similar.map((item, idx) => (
                <Grid item xs={6} sm={4} md={2.4} key={idx}>
                  <Card
                    component={RouterLink}
                    to={`/product/${item.product?.id}`}
                    elevation={0}
                    sx={{
                      textDecoration: 'none',
                      borderRadius: '12px',
                      border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`,
                      transition: 'all 0.3s ease',
                      '&:hover': { transform: 'translateY(-4px)', boxShadow: `0 8px 20px ${alpha('#000', 0.08)}` },
                    }}
                  >
                    <Box sx={{ p: 1.5, height: 120, display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: '#fafafa' }}>
                      <Box
                        component="img"
                        src={item.product?.image_url || 'https://placehold.co/150x150'}
                        alt={item.product?.name}
                        sx={{ maxWidth: '90%', maxHeight: '90%', objectFit: 'contain' }}
                        onError={(e) => { e.target.src = 'https://placehold.co/150x150'; }}
                      />
                    </Box>
                    <CardContent sx={{ p: 1.5, pb: '12px !important' }}>
                      <Typography variant="caption" sx={{ fontWeight: 600, display: 'block', lineHeight: 1.3, mb: 0.3 }}>
                        {item.product?.name}
                      </Typography>
                      <Typography variant="body2" sx={{ fontWeight: 800 }}>
                        ₹{item.product?.price?.toLocaleString()}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Box>
        )}

        {/* Frequently Bought Together */}
        {frequentlyBought.length > 0 && (
          <Box sx={{ mt: 6 }}>
            <Typography variant="h5" sx={{ fontWeight: 700, mb: 3 }}>Frequently Bought Together</Typography>
            <Grid container spacing={2}>
              {frequentlyBought.map((item, idx) => (
                <Grid item xs={6} sm={4} md={2.4} key={idx}>
                  <Card
                    component={RouterLink}
                    to={`/product/${item.product?.id}`}
                    elevation={0}
                    sx={{
                      textDecoration: 'none',
                      borderRadius: '12px',
                      border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`,
                      transition: 'all 0.3s ease',
                      '&:hover': { transform: 'translateY(-4px)', boxShadow: `0 8px 20px ${alpha('#000', 0.08)}` },
                    }}
                  >
                    <Box sx={{ p: 1.5, height: 120, display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: '#fafafa' }}>
                      <Box
                        component="img"
                        src={item.product?.image_url || 'https://placehold.co/150x150'}
                        alt={item.product?.name}
                        sx={{ maxWidth: '90%', maxHeight: '90%', objectFit: 'contain' }}
                        onError={(e) => { e.target.src = 'https://placehold.co/150x150'; }}
                      />
                    </Box>
                    <CardContent sx={{ p: 1.5, pb: '12px !important' }}>
                      <Typography variant="caption" sx={{ fontWeight: 600, display: 'block', lineHeight: 1.3, mb: 0.3 }}>
                        {item.product?.name}
                      </Typography>
                      <Typography variant="body2" sx={{ fontWeight: 800 }}>
                        ₹{item.product?.price?.toLocaleString()}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Box>
        )}

        {/* Recommended For You + Why This Product */}
        {(recommended.length > 0 || whyThis.length > 0) && (
          <Box sx={{ mt: 6 }}>
            <Typography variant="h5" sx={{ fontWeight: 700, mb: 1 }}>Recommended For You</Typography>
            {whyThis.length > 0 && (
              <Paper sx={{ p: 2.5, mb: 3, borderRadius: '16px', bgcolor: alpha(theme.palette.primary.main, 0.04) }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1 }}>Why This Product?</Typography>
                {whyThis.map((reason, i) => (
                  <Box key={i} sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                    <CheckCircle sx={{ fontSize: 16, color: 'success.main' }} />
                    <Typography variant="body2">{reason}</Typography>
                  </Box>
                ))}
              </Paper>
            )}
            <Grid container spacing={2}>
              {recommended.map((item, idx) => (
                <Grid item xs={6} sm={4} md={2.4} key={idx}>
                  <Card component={RouterLink} to={`/product/${item.product?.id}`} elevation={0}
                    sx={{ textDecoration: 'none', borderRadius: '12px', border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}` }}>
                    <Box sx={{ p: 1.5, height: 120, display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: '#fafafa' }}>
                      <Box component="img" src={item.product?.image_url || 'https://placehold.co/150x150'}
                        alt={item.product?.name} sx={{ maxWidth: '90%', maxHeight: '90%', objectFit: 'contain' }} />
                    </Box>
                    <CardContent sx={{ p: 1.5, pb: '12px !important' }}>
                      <Typography variant="caption" sx={{ fontWeight: 600, display: 'block', lineHeight: 1.3, mb: 0.3 }}>
                        {item.product?.name}
                      </Typography>
                      <Typography variant="body2" sx={{ fontWeight: 800 }}>₹{item.product?.price?.toLocaleString()}</Typography>
                      <Typography variant="caption" color="text.secondary">Score: {(item.score * 100).toFixed(0)}/100</Typography>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Box>
        )}

        {/* Reviews Section */}
        {product.reviews?.length > 0 && (
          <Box sx={{ mt: 6 }}>
            <Divider sx={{ mb: 4 }} />
            <Typography variant="h5" sx={{ fontWeight: 700, mb: 3 }}>Customer Reviews</Typography>
            <Grid container spacing={2}>
              {product.reviews.slice(0, 6).map((review, idx) => (
                <Grid item xs={12} sm={6} key={idx}>
                  <Paper sx={{ p: 2, borderRadius: '12px' }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                      <Rating value={review.rating || 0} readOnly size="small" />
                      <Chip
                        label={review.sentiment || 'neutral'}
                        size="small"
                        color={review.sentiment === 'positive' ? 'success' : review.sentiment === 'negative' ? 'error' : 'default'}
                        sx={{ fontWeight: 600, textTransform: 'capitalize' }}
                      />
                    </Box>
                    <Typography variant="body2" sx={{ lineHeight: 1.6, color: 'text.secondary' }}>
                      {review.text?.slice(0, 200)}{review.text?.length > 200 ? '...' : ''}
                    </Typography>
                  </Paper>
                </Grid>
              ))}
            </Grid>
          </Box>
        )}
      </Box>
    </Container>
  );
};

export default ProductDetails;