import api from './api';

const orderService = {
  getOrders: async (userId) => {
    const response = await api.get(`/orders/${userId}`);
    return response.data;
  },

  getOrderDetail: async (orderId) => {
    const response = await api.get(`/orders/detail/${orderId}`);
    return response.data;
  },
};

export default orderService;
