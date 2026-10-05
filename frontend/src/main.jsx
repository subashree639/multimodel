import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { CssBaseline } from '@mui/material';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import App from './App';
import './styles/global.css';
import { AuthProvider } from './context/AuthContext';
import { ThemeProvider as CustomThemeProvider } from './context/ThemeContext';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <BrowserRouter>
    <CustomThemeProvider>
      <AuthProvider>
        <CssBaseline />
        <App />
        <ToastContainer position="top-right" autoClose={3000} />
      </AuthProvider>
    </CustomThemeProvider>
  </BrowserRouter>
);