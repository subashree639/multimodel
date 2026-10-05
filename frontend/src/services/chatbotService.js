import api from './api';

const chatbotService = {
  sendMessage: async (message, userId = 'guest') => {
    const response = await api.post('/chat', { message, user_id: userId });
    return response.data;
  },
};

export default chatbotService;