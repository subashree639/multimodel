import { Card, CardContent, Typography, Box, Chip, Button, useTheme, alpha } from '@mui/material';
import { Star, TrendingUp, Visibility, CheckCircle } from '@mui/icons-material';
import { Link as RouterLink } from 'react-router-dom';

const RecommendationCard = ({ recommendation }) => {
  const { product_id, name, price, image, image_url, score, reason, is_trending, explanation } = recommendation;
  const theme = useTheme();
  const displayImage = image_url || image || '/images/placeholder.png';

  // Extract why_recommended from explanation
  const whyRecommended = explanation?.why_recommended || [];
  const displayScore = score ? Math.round(score * 100) : null;

  return (
    <Card
      elevation={0}
      sx={{
        borderRadius: '16px',
        border: `1px solid ${alpha(theme.palette.primary.main, 0.3)}`,
        transition: 'all 0.3s ease',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        '&:hover': {
          transform: 'translateY(-5px)',
          boxShadow: `0 12px 24px ${alpha(theme.palette.primary.main, 0.15)}`,
          borderColor: theme.palette.primary.main,
        },
      }}
    >
      <Box sx={{ p: 2, display: 'flex', justifyContent: 'center', alignItems: 'center', height: 160, backgroundColor: '#fafafa', borderRadius: '16px 16px 0 0', position: 'relative' }}>
        <Box
          component="img"
          src={displayImage}
          alt={name}
          sx={{ maxWidth: '90%', maxHeight: '90%', objectFit: 'contain' }}
          onError={(e) => { e.target.src = 'https://placehold.co/200x200?text=Product'; }}
        />
        {(is_trending || explanation?.is_trending) && (
          <Chip
            icon={<TrendingUp sx={{ fontSize: '14px !important' }} />}
            label="Trending"
            size="small"
            color="error"
            sx={{ position: 'absolute', top: 10, right: 10, fontWeight: 600, boxShadow: '0 4px 8px rgba(0,0,0,0.1)' }}
          />
        )}
      </Box>
      <CardContent sx={{ flexGrow: 1, pt: 2, pb: '12px !important' }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 700, lineHeight: 1.2, mb: 0.5, height: 44, overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
          {name}
        </Typography>
        <Typography variant="h6" sx={{ fontWeight: 800, color: 'text.primary', mb: 1 }}>
          ₹{price?.toLocaleString() || '0'}
        </Typography>

        {/* Score Badge */}
        {displayScore && (
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 1.5, bgcolor: alpha(theme.palette.primary.main, 0.1), p: 0.5, borderRadius: 1, width: 'fit-content', pr: 1.5 }}>
            <Star color="primary" sx={{ fontSize: 18 }} />
            <Typography variant="body2" sx={{ ml: 0.5, fontWeight: 700, color: 'primary.main' }}>
              Score: {displayScore}/100
            </Typography>
          </Box>
        )}

        {/* Why Recommended Checklist */}
        {whyRecommended.length > 0 && (
          <Box sx={{ mb: 1 }}>
            <Typography variant="caption" sx={{ fontWeight: 700, color: 'text.secondary', display: 'block', mb: 0.5 }}>
              Why Recommended?
            </Typography>
            {whyRecommended.map((reason, i) => (
              <Box key={i} sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.3 }}>
                <CheckCircle sx={{ fontSize: 14, color: 'success.main' }} />
                <Typography variant="caption" sx={{ color: 'success.main', fontWeight: 500 }}>
                  {reason}
                </Typography>
              </Box>
            ))}
          </Box>
        )}

        {/* Fallback reason text */}
        {whyRecommended.length === 0 && reason && (
          <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.8rem', lineHeight: 1.4, height: 36, overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
            {typeof reason === 'string' ? reason : reason?.reason || ''}
          </Typography>
        )}
      </CardContent>
      <Box sx={{ px: 2, pb: 2, pt: 0 }}>
        <Button
          fullWidth
          component={RouterLink}
          to={`/product/${product_id}`}
          variant="outlined"
          endIcon={<Visibility />}
          sx={{
            borderRadius: '8px',
            textTransform: 'none',
            fontWeight: 600,
            borderWidth: '2px',
            '&:hover': { borderWidth: '2px' },
          }}
        >
          View Details
        </Button>
      </Box>
    </Card>
  );
};

export default RecommendationCard;