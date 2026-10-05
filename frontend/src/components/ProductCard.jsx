import { Card, CardContent, Typography, Rating, CardActions, Button, Box, Chip, useTheme, alpha } from '@mui/material';
import { Favorite, ShoppingCart, Visibility, TrendingUp } from '@mui/icons-material';
import { Link as RouterLink } from 'react-router-dom';

const ProductCard = ({ product, onAddToWishlist, onAddToCart }) => {
  const { id, name, category, price, image, image_path, rating, avg_rating, description, is_trending, num_reviews } = product;
  const theme = useTheme();
  const displayImage = image_path || image || '/images/placeholder.png';
  const displayRating = avg_rating || rating || 0;

  return (
    <Card
      elevation={0}
      sx={{
        borderRadius: '16px',
        border: `1px solid ${alpha(theme.palette.primary.main, 0.25)}`,
        transition: 'all 0.3s ease',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
        '&:hover': {
          transform: 'translateY(-5px)',
          boxShadow: `0 12px 24px ${alpha(theme.palette.primary.main, 0.15)}`,
          borderColor: theme.palette.primary.main,
        },
      }}
    >
      {is_trending && (
        <Chip
          icon={<TrendingUp sx={{ fontSize: '14px !important' }} />}
          label="Trending"
          size="small"
          color="error"
          sx={{ position: 'absolute', top: 10, right: 10, zIndex: 2, fontWeight: 600, boxShadow: '0 4px 8px rgba(0,0,0,0.1)' }}
        />
      )}
      <Box sx={{ p: 2, display: 'flex', justifyContent: 'center', alignItems: 'center', height: 200, backgroundColor: '#fafafa', borderRadius: '16px 16px 0 0' }}>
        <Box
          component="img"
          src={displayImage}
          alt={name}
          sx={{ maxWidth: '90%', maxHeight: '90%', objectFit: 'contain' }}
          onError={(e) => { e.target.src = 'https://placehold.co/200x200?text=Product'; }}
        />
      </Box>
      <CardContent sx={{ flexGrow: 1, pt: 2, pb: '12px !important' }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 700, lineHeight: 1.2, mb: 0.5, height: 44, overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
          {name}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
          {category}
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 0.5 }}>
          <Rating value={displayRating} precision={0.5} readOnly size="small" />
          <Typography variant="caption" sx={{ ml: 0.5, fontWeight: 600 }}>
            {displayRating > 0 ? displayRating.toFixed(1) : '0'} {num_reviews ? `(${num_reviews})` : ''}
          </Typography>
        </Box>
        <Typography variant="h6" sx={{ fontWeight: 800, color: 'text.primary' }}>
          ₹{price?.toLocaleString() || '0'}
        </Typography>
      </CardContent>
      <CardActions sx={{ px: 2, pb: 2, pt: 0, justifyContent: 'space-between' }}>
        <Box>
          <Button size="small" component={RouterLink} to={`/product/${id}`} sx={{ minWidth: 'auto', mr: 1 }}>
            <Visibility />
          </Button>
          <Button size="small" onClick={() => onAddToWishlist?.(id)} sx={{ minWidth: 'auto' }}>
            <Favorite />
          </Button>
        </Box>
        <Button
          size="small"
          variant="contained"
          startIcon={<ShoppingCart />}
          onClick={() => onAddToCart?.(id)}
          sx={{
            borderRadius: '8px',
            textTransform: 'none',
            fontWeight: 600,
            boxShadow: 'none',
            '&:hover': {
              boxShadow: `0 4px 8px ${alpha(theme.palette.primary.main, 0.3)}`,
            },
          }}
        >
          Add
        </Button>
      </CardActions>
    </Card>
  );
};

export default ProductCard;