import api from './api';

const recommendationService = {
  getRecommendations: async (userId) => {
    const response = await api.get(`/recommendations/${userId}`);
    return response.data;
  },

  getProduct: async (id) => {
    const response = await api.get(`/products/${id}`);
    return response.data;
  },

  getTrendingProducts: async () => {
    const response = await api.get('/products/trending');
    return response.data;
  },
};

export default recommendationService;