import api from './api';

const sentimentService = {
  analyzeReview: async (data) => {
    const response = await api.post('/reviews/analyze', data);
    return response.data;
  },

  getProductReviews: async (productId) => {
    const response = await api.get(`/reviews/product/${productId}`);
    return response.data;
  },
};

export default sentimentService;