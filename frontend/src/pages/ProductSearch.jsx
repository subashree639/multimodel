import { useState, useEffect } from 'react';
import { Container, Grid, Box, Typography, Pagination, FormControl, InputLabel, Select, MenuItem } from '@mui/material';
import { useSearchParams } from 'react-router-dom';
import { toast } from 'react-toastify';
import { useAuth } from '../context/AuthContext';
import ProductCard from '../components/ProductCard';
import SearchBar from '../components/SearchBar';
import Loader from '../components/Loader';
import cartService from '../services/cartService';
import wishlistService from '../services/wishlistService';
import config from '../config';

const ProductSearch = () => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [sortBy, setSortBy] = useState('name');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [categories, setCategories] = useState([]);
  const { user, isAuthenticated } = useAuth();
  const [searchParams] = useSearchParams();

  // Read category from URL params
  useEffect(() => {
    const urlCategory = searchParams.get('category');
    if (urlCategory) setCategory(urlCategory);
  }, [searchParams]);

  // Fetch categories from API
  useEffect(() => {
    fetch(`${config.API_BASE_URL}/products/categories`)
      .then((r) => r.json())
      .then((data) => setCategories(data.categories || []))
      .catch(() => setCategories(['Electronics', 'Clothing', 'Home', 'Sports', 'Books']));
  }, []);

  useEffect(() => {
    const fetchProducts = async () => {
      setLoading(true);
      try {
        const queryParams = new URLSearchParams({ page, sort_by: sortBy });
        if (search) queryParams.append('search', search);
        if (category && category !== 'All') queryParams.append('category', category);

        const response = await fetch(`${config.API_BASE_URL}/products?${queryParams}`);
        if (!response.ok) throw new Error('Network response was not ok');
        const data = await response.json();

        setProducts(data.products || []);
        setTotalPages(data.pages || 1);
      } catch (error) {
        console.error('Failed to fetch products:', error);
        setProducts([]);
        setTotalPages(1);
      } finally {
        setLoading(false);
      }
    };

    const timeoutId = setTimeout(() => { fetchProducts(); }, 400);
    return () => clearTimeout(timeoutId);
  }, [page, category, sortBy, search]);

  const handleAddToCart = async (productId) => {
    if (!isAuthenticated) { toast.info('Please login to add items to cart'); return; }
    try {
      const userId = user?.user_id || user?.sub || '';
      await cartService.addToCart(userId, productId);
      toast.success('Added to cart!');
    } catch (error) {
      toast.error('Failed to add to cart');
    }
  };

  const handleWishlist = async (productId) => {
    if (!isAuthenticated) { toast.info('Please login to add to wishlist'); return; }
    try {
      const userId = user?.user_id || user?.sub || '';
      await wishlistService.addToWishlist(userId, productId);
      toast.success('Added to wishlist!');
    } catch (error) {
      toast.error('Failed to add to wishlist');
    }
  };

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
          Browse Products
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          {products.length > 0 ? `Showing ${products.length} products` : 'Search our catalog'}
        </Typography>

        <Box sx={{ mb: 3 }}>
          <SearchBar value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} />
        </Box>

        <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
          <FormControl sx={{ minWidth: 180 }} size="small">
            <InputLabel>Category</InputLabel>
            <Select value={category} label="Category" onChange={(e) => { setCategory(e.target.value); setPage(1); }}>
              <MenuItem value="">All Categories</MenuItem>
              {categories.map((cat) => (
                <MenuItem key={cat} value={cat}>{cat}</MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl sx={{ minWidth: 180 }} size="small">
            <InputLabel>Sort By</InputLabel>
            <Select value={sortBy} label="Sort By" onChange={(e) => setSortBy(e.target.value)}>
              <MenuItem value="name">Name</MenuItem>
              <MenuItem value="price">Price: Low to High</MenuItem>
              <MenuItem value="price_desc">Price: High to Low</MenuItem>
              <MenuItem value="rating">Top Rated</MenuItem>
            </Select>
          </FormControl>
        </Box>

        {loading ? (
          <Loader />
        ) : products.length === 0 ? (
          <Box sx={{ textAlign: 'center', py: 8 }}>
            <Typography variant="h6" color="text.secondary">No products found</Typography>
            <Typography variant="body2" color="text.secondary">Try adjusting your search or filters</Typography>
          </Box>
        ) : (
          <>
            <Grid container spacing={3}>
              {products.map((product) => (
                <Grid item xs={12} sm={6} md={4} key={product.id}>
                  <ProductCard
                    product={{
                      ...product,
                      image: product.image_url || product.image,
                      rating: product.avg_rating || product.rating || 0,
                    }}
                    onAddToWishlist={handleWishlist}
                    onAddToCart={handleAddToCart}
                  />
                </Grid>
              ))}
            </Grid>

            {totalPages > 1 && (
              <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
                <Pagination count={totalPages} page={page} onChange={(e, v) => setPage(v)} color="primary" />
              </Box>
            )}
          </>
        )}
      </Box>
    </Container>
  );
};

export default ProductSearch;