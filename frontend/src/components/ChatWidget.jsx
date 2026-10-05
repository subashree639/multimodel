import { useState, useRef, useEffect } from 'react';
import { Box, TextField, IconButton, Paper, Typography, Avatar, Chip } from '@mui/material';
import { Send, SmartToy, Person } from '@mui/icons-material';

const ChatWidget = ({ onSendMessage, messages = [] }) => {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = () => {
    if (input.trim()) {
      onSendMessage(input);
      setInput('');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSend();
    }
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Box sx={{ flexGrow: 1, overflowY: 'auto', p: 2, maxHeight: 400 }}>
        {messages.map((msg, index) => (
          <Box
            key={index}
            sx={{
              display: 'flex',
              mb: 2,
              flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
            }}
          >
            <Avatar sx={{ mx: 1 }}>
              {msg.role === 'user' ? <Person /> : <SmartToy />}
            </Avatar>
            <Paper
              sx={{
                p: 1.5,
                bgcolor: msg.role === 'user' ? 'primary.main' : 'background.paper',
                color: msg.role === 'user' ? 'primary.contrastText' : 'text.primary',
                maxWidth: '70%',
              }}
            >
              <Typography variant="body2">{msg.content}</Typography>
              {msg.products && (
                <Box sx={{ mt: 1 }}>
                  {msg.products.map((p) => (
                    <Chip key={p.id} label={p.name} size="small" sx={{ mr: 0.5, mt: 0.5 }} />
                  ))}
                </Box>
              )}
            </Paper>
          </Box>
        ))}
        <div ref={messagesEndRef} />
      </Box>
      <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
        <TextField
          fullWidth
          placeholder="Ask about products..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          InputProps={{
            endAdornment: (
              <IconButton onClick={handleSend} disabled={!input.trim()}>
                <Send />
              </IconButton>
            ),
          }}
          size="small"
        />
      </Box>
    </Box>
  );
};

export default ChatWidget;