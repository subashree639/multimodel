import api from './api';

const wishlistService = {
  getWishlist: async (userId) => {
    const response = await api.get(`/wishlist/${userId}`);
    return response.data;
  },

  addToWishlist: async (userId, productId) => {
    const response = await api.post('/wishlist/add', {
      user_id: userId,
      product_id: productId,
    });
    return response.data;
  },

  removeFromWishlist: async (userId, productId) => {
    const response = await api.delete(`/wishlist/remove/${userId}/${productId}`);
    return response.data;
  },
};

export default wishlistService;
