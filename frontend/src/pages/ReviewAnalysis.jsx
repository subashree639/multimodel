import { Container, Box, Typography, Paper, TextField, Button, Grid, Chip, alpha, useTheme } from '@mui/material';
import { Psychology, RateReview } from '@mui/icons-material';
import { useState } from 'react';
import { toast } from 'react-toastify';
import sentimentService from '../services/sentimentService';
import ReviewChart from '../components/ReviewChart';

const ReviewAnalysis = () => {
  const [reviewText, setReviewText] = useState('');
  const [rating, setRating] = useState(3);
  const [productId, setProductId] = useState('test');
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const theme = useTheme();

  const handleAnalyze = async () => {
    if (!reviewText.trim()) {
      toast.error('Please enter a review');
      return;
    }
    setLoading(true);
    try {
      const result = await sentimentService.analyzeReview({
        product_id: productId,
        text: reviewText,
        rating,
      });
      setAnalysis(result);
      toast.success('Analysis complete!');
    } catch (error) {
      toast.error('Analysis failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="md">
      <Box sx={{ py: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
          <Psychology sx={{ fontSize: 40, color: 'primary.main', mr: 2 }} />
          <Box>
            <Typography variant="h4" sx={{ fontWeight: 700 }}>AI Sentiment Analysis</Typography>
            <Typography color="text.secondary">Test the RoBERTa sentiment engine</Typography>
          </Box>
        </Box>

        <Paper elevation={0} sx={{ p: 4, mb: 4, border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`, borderRadius: '16px' }}>
          <TextField
            fullWidth
            label="Product ID (optional)"
            value={productId}
            onChange={(e) => setProductId(e.target.value)}
            margin="normal"
            size="small"
          />
          <TextField
            fullWidth
            label="Review Text"
            placeholder="Type a product review here..."
            multiline
            rows={5}
            value={reviewText}
            onChange={(e) => setReviewText(e.target.value)}
            margin="normal"
          />
          <TextField
            select
            fullWidth
            label="Rating"
            value={rating}
            onChange={(e) => setRating(Number(e.target.value))}
            margin="normal"
            SelectProps={{ native: true }}
            size="small"
          >
            {[1, 2, 3, 4, 5].map((n) => (
              <option key={n} value={n}>{n} Star{n > 1 ? 's' : ''}</option>
            ))}
          </TextField>

          <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 3 }}>
            <Button
              variant="contained"
              onClick={handleAnalyze}
              disabled={loading}
              size="large"
              startIcon={<RateReview />}
              sx={{ fontWeight: 700 }}
            >
              {loading ? 'Analyzing...' : 'Analyze Sentiment'}
            </Button>
          </Box>
        </Paper>

        {analysis && (
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Paper elevation={0} sx={{ p: 3, border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`, borderRadius: '16px', height: '100%' }}>
                <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>Analysis Results</Typography>
                <Box sx={{ mb: 3 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>Overall Sentiment</Typography>
                  <Chip
                    label={analysis.sentiment.toUpperCase()}
                    color={analysis.sentiment === 'positive' ? 'success' : analysis.sentiment === 'negative' ? 'error' : 'default'}
                    sx={{ fontWeight: 700, fontSize: '1rem', py: 2 }}
                  />
                </Box>
                {analysis.keywords && analysis.keywords.length > 0 && (
                  <Box>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>Extracted Keywords</Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                      {analysis.keywords.map((kw, i) => (
                        <Chip key={i} label={kw} size="small" variant="outlined" />
                      ))}
                    </Box>
                  </Box>
                )}
              </Paper>
            </Grid>
            <Grid item xs={12} md={6}>
              <Paper elevation={0} sx={{ p: 3, border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`, borderRadius: '16px', height: '100%' }}>
                <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>Sentiment Breakdown</Typography>
                {/* Convert 0-1 values to percentages for the chart */}
                <ReviewChart
                  sentimentData={{
                    positive: Math.round(analysis.scores.positive * 100),
                    neutral: Math.round(analysis.scores.neutral * 100),
                    negative: Math.round(analysis.scores.negative * 100),
                  }}
                />
              </Paper>
            </Grid>
          </Grid>
        )}
      </Box>
    </Container>
  );
};

export default ReviewAnalysis;