import api from './api';

const cartService = {
  getCart: async (userId) => {
    const response = await api.get(`/cart/${userId}`);
    return response.data;
  },

  addToCart: async (userId, productId, quantity = 1) => {
    const response = await api.post('/cart/add', {
      user_id: userId,
      product_id: productId,
      quantity,
    });
    return response.data;
  },

  removeFromCart: async (userId, productId) => {
    const response = await api.delete(`/cart/remove/${userId}/${productId}`);
    return response.data;
  },

  checkout: async (userId) => {
    const response = await api.post(`/cart/checkout/${userId}`);
    return response.data;
  },
};

export default cartService;
