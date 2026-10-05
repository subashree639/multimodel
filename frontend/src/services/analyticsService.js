import api from './api';

const analyticsService = {
  getSalesAnalytics: async () => {
    const response = await api.get('/admin/sales-analytics');
    return response.data;
  },

  getCustomerSegments: async () => {
    const response = await api.get('/admin/customer-segments');
    return response.data;
  },
};

export default analyticsService;
