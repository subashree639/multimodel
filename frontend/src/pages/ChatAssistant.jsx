import { useState, useRef, useEffect } from 'react';
import { Container, Box, Typography, Paper, TextField, IconButton, Avatar, Chip, useTheme, alpha } from '@mui/material';
import { Send, SmartToy, Person } from '@mui/icons-material';
import chatbotService from '../services/chatbotService';
import { useAuth } from '../context/AuthContext';
import { Link as RouterLink } from 'react-router-dom';

const ChatWidget = ({ messages, onSendMessage }) => {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);
  const theme = useTheme();

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    if (input.trim()) {
      onSendMessage(input);
      setInput('');
    }
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Box sx={{ flexGrow: 1, overflowY: 'auto', p: 3, display: 'flex', flexDirection: 'column', gap: 3 }}>
        {messages.map((msg, index) => (
          <Box
            key={index}
            sx={{
              display: 'flex',
              flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
              alignItems: 'flex-start',
              gap: 2,
            }}
          >
            <Avatar sx={{ bgcolor: msg.role === 'user' ? 'primary.main' : 'secondary.main' }}>
              {msg.role === 'user' ? <Person /> : <SmartToy />}
            </Avatar>
            <Box sx={{ maxWidth: '80%' }}>
              <Paper
                elevation={0}
                sx={{
                  p: 2,
                  bgcolor: msg.role === 'user' ? alpha(theme.palette.primary.main, 0.1) : '#fafafa',
                  border: `1px solid ${alpha(theme.palette.primary.main, msg.role === 'user' ? 0.3 : 0.1)}`,
                  borderRadius: msg.role === 'user' ? '16px 4px 16px 16px' : '4px 16px 16px 16px',
                }}
              >
                <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{msg.content}</Typography>
              </Paper>
              {msg.products && msg.products.length > 0 && (
                <Box sx={{ mt: 2, display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {msg.products.map((p) => (
                    <Chip
                      key={p.product_id || p.id}
                      label={`${p.name} - ₹${p.price}`}
                      component={RouterLink}
                      to={`/product/${p.product_id || p.id}`}
                      clickable
                      color="primary"
                      variant="outlined"
                      sx={{ bgcolor: 'background.paper', fontWeight: 600 }}
                    />
                  ))}
                </Box>
              )}
            </Box>
          </Box>
        ))}
        <div ref={messagesEndRef} />
      </Box>
      <Box sx={{ p: 2, borderTop: `1px solid ${alpha(theme.palette.primary.main, 0.1)}`, bgcolor: 'background.paper' }}>
        <TextField
          fullWidth
          placeholder="Ask me anything..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSend()}
          InputProps={{
            endAdornment: (
              <IconButton onClick={handleSend} disabled={!input.trim()} color="primary">
                <Send />
              </IconButton>
            ),
            sx: { borderRadius: '24px', bgcolor: '#fafafa' }
          }}
        />
      </Box>
    </Box>
  );
};

const ChatAssistant = () => {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hello! I am your AI Shopping Assistant. I can help you find products, compare options, and answer questions about anything in our catalog. What are you looking for today?' },
  ]);
  const { user } = useAuth();
  const theme = useTheme();

  const handleSendMessage = async (message) => {
    const userMessage = { role: 'user', content: message };
    setMessages((prev) => [...prev, userMessage]);

    try {
      const response = await chatbotService.sendMessage(message, user?.user_id || 'guest');
      const botMessage = { role: 'assistant', content: response.response, products: response.relevant_products };
      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      const botMessage = {
        role: 'assistant',
        content: `I'm sorry, I'm having trouble connecting to my brain right now. Please try again later.`,
      };
      setMessages((prev) => [...prev, botMessage]);
    }
  };

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4, height: 'calc(100vh - 100px)' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
          <SmartToy sx={{ fontSize: 40, color: 'primary.main', mr: 2 }} />
          <Box>
            <Typography variant="h4" sx={{ fontWeight: 700 }}>AI Shopping Assistant</Typography>
            <Typography color="text.secondary">Powered by RAG and Semantic Search</Typography>
          </Box>
        </Box>

        <Paper
          elevation={0}
          sx={{
            height: 'calc(100% - 100px)',
            border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`,
            borderRadius: '24px',
            overflow: 'hidden',
          }}
        >
          <ChatWidget messages={messages} onSendMessage={handleSendMessage} />
        </Paper>
      </Box>
    </Container>
  );
};

export default ChatAssistant;