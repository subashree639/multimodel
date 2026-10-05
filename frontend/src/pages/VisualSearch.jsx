import { useState } from 'react';
import { Container, Box, Typography, Paper, Button, Grid, Card, CardContent, useTheme, alpha, LinearProgress } from '@mui/material';
import { CloudUpload, ImageSearch, CheckCircle } from '@mui/icons-material';
import config from '../config';

const VisualSearch = () => {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [fallback, setFallback] = useState('');
  const theme = useTheme();

  const handleFile = (e) => {
    const f = e.target.files?.[0];
    setError('');
    setFallback('');
    if (!f) return;
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(f.type)) {
      setError('Please upload a JPG, PNG or WEBP image.');
      return;
    }
    if (f.size > 10 * 1024 * 1024) {
      setError('Image too large (max 10MB).');
      return;
    }
    setFile(f);
    setPreview(URL.createObjectURL(f));
  };

  const handleSearch = async () => {
    if (!file) return;
    setLoading(true);
    setError('');
    try {
      const form = new FormData();
      form.append('file', file);
      const res = await fetch(`${config.API_BASE_URL}/images/search?top_k=10`, { method: 'POST', body: form });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Visual search failed');
      }
      const data = await res.json();
      setResults(data.results || []);
      if (data.fallback) setFallback(`Visual index unavailable (${data.fallback}) — showing popular items instead.`);
    } catch (e) {
      setError(e.message);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
          <ImageSearch sx={{ fontSize: 36, color: 'primary.main', mr: 1.5 }} />
          <Typography variant="h4" sx={{ fontWeight: 700 }}>Visual Search</Typography>
        </Box>
        <Typography color="text.secondary" sx={{ mb: 3 }}>
          Upload a product image to find visually similar items (ResNet50 embeddings + FAISS), re-ranked for you.
        </Typography>

        <Paper sx={{ p: 3, borderRadius: '20px', border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`, mb: 3 }}>
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
            <Button variant="outlined" component="label" startIcon={<CloudUpload />}>
              Upload Product Image
              <input type="file" hidden accept="image/jpeg,image/png,image/webp" onChange={handleFile} />
            </Button>
            <Button variant="contained" disabled={!file || loading} onClick={handleSearch}>
              Find Similar Products
            </Button>
          </Box>
          {preview && (
            <Box sx={{ mt: 2, display: 'flex', justifyContent: 'center' }}>
              <Box component="img" src={preview} alt="query" sx={{ maxHeight: 220, borderRadius: '12px', border: '1px solid #eee' }} />
            </Box>
          )}
          {loading && <LinearProgress sx={{ mt: 2 }} />}
          {error && <Typography color="error" sx={{ mt: 2 }}>{error}</Typography>}
          {fallback && <Typography color="text.secondary" sx={{ mt: 2 }}>{fallback}</Typography>}
        </Paper>

        {results.length > 0 && (
          <>
            <Typography variant="h5" sx={{ fontWeight: 700, mb: 2 }}>Similar Products ({results.length})</Typography>
            <Grid container spacing={2}>
              {results.map((r, idx) => (
                <Grid item xs={6} sm={4} md={2.4} key={idx}>
                  <Card sx={{ borderRadius: '12px', border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}` }}>
                    <Box sx={{ p: 1.5, height: 120, display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: '#fafafa' }}>
                      <Box component="img" src={r.product?.image_url || 'https://placehold.co/150x150'} alt={r.product?.name}
                        sx={{ maxWidth: '90%', maxHeight: '90%', objectFit: 'contain' }} />
                    </Box>
                    <CardContent sx={{ p: 1.5 }}>
                      <Typography variant="caption" sx={{ fontWeight: 600, display: 'block', lineHeight: 1.3, mb: 0.5 }}>
                        {r.product?.name}
                      </Typography>
                      <Typography variant="body2" sx={{ fontWeight: 800 }}>₹{r.product?.price?.toLocaleString()}</Typography>
                      {r.similarity_score > 0 && (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.5 }}>
                          <CheckCircle sx={{ fontSize: 14, color: 'success.main' }} />
                          <Typography variant="caption" color="success.main">
                            {(r.similarity_score * 100).toFixed(1)}% match
                          </Typography>
                        </Box>
                      )}
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </>
        )}
      </Box>
    </Container>
  );
};

export default VisualSearch;
