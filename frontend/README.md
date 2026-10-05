# Recomora - React Frontend

A modern React.js frontend for the Recomora AI Product Recommendation System.

## Features

- Modern e-commerce UI with Material UI
- Responsive design for mobile and desktop
- JWT Authentication with protected routes
- Product search and filtering
- AI-powered recommendations
- Chat assistant interface
- Sales analytics dashboard
- Review sentiment analysis
- Dark/Light mode toggle
- Wishlist functionality

## Setup Instructions

### Prerequisites
- Node.js 18+ installed
- npm or yarn package manager
- FastAPI backend running on `http://localhost:8000`

### Installation

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:5173`

### Build for Production

```bash
npm run build
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── components/     # Reusable UI components
│   ├── pages/         # Route pages
│   ├── services/      # API service layers
│   ├── context/       # React context providers
│   ├── styles/        # CSS stylesheets
│   └── routes/        # Route definitions
```

## Backend Integration

The frontend connects to the FastAPI backend via Axios. Ensure the backend is running:

```bash
# From project root
python run_server.py
```

## API Endpoints

- POST `/api/v1/auth/register` - Register new user
- POST `/api/v1/auth/login` - User login
- GET `/api/v1/products` - List products
- GET `/api/v1/recommendations/{user_id}` - Get recommendations
- POST `/api/v1/reviews/analyze` - Analyze review sentiment
- GET `/api/v1/chat` - Chat with AI assistant
- GET `/api/v1/admin/sales-analytics` - Get sales analytics