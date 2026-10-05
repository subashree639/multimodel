import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Home from '../pages/Home';
import Login from '../pages/Login';
import Register from '../pages/Register';
import ProductSearch from '../pages/ProductSearch';
import Recommendations from '../pages/Recommendations';
import ProductDetails from '../pages/ProductDetails';
import Dashboard from '../pages/Dashboard';
import ReviewAnalysis from '../pages/ReviewAnalysis';
import ChatAssistant from '../pages/ChatAssistant';
import VisualSearch from '../pages/VisualSearch';
import SalesAnalytics from '../pages/SalesAnalytics';
import Profile from '../pages/Profile';
import Settings from '../pages/Settings';
import Cart from '../pages/Cart';
import Wishlist from '../pages/Wishlist';
import Orders from '../pages/Orders';

const PrivateRoute = ({ children }) => {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? children : <Navigate to="/login" />;
};

const AppRoutes = () => {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/products" element={<ProductSearch />} />
      <Route path="/product/:id" element={<ProductDetails />} />
      <Route path="/recommendations" element={<Recommendations />} />
      <Route path="/reviews" element={<ReviewAnalysis />} />
      <Route path="/chat" element={<ChatAssistant />} />
      <Route path="/visual-search" element={<VisualSearch />} />
      <Route path="/analytics" element={<SalesAnalytics />} />
      <Route path="/cart" element={<PrivateRoute><Cart /></PrivateRoute>} />
      <Route path="/wishlist" element={<PrivateRoute><Wishlist /></PrivateRoute>} />
      <Route path="/orders" element={<PrivateRoute><Orders /></PrivateRoute>} />
      <Route path="/dashboard" element={<PrivateRoute><Dashboard /></PrivateRoute>} />
      <Route path="/profile" element={<PrivateRoute><Profile /></PrivateRoute>} />
      <Route path="/settings" element={<PrivateRoute><Settings /></PrivateRoute>} />
    </Routes>
  );
};

export default AppRoutes;