"""
Database schema definitions and Pydantic models.
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

try:
    from bson import ObjectId
except ImportError:
    ObjectId = str  # type: ignore


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, str) and not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return v

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string", format="object-id")


# ==================== USER SCHEMA ====================

class UserBase(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    email: EmailStr
    name: str
    preferences: Dict[str, Any] = {}


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class User(UserBase):
    id: str = Field(alias="_id", default=None)
    hashed_password: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    preferences: Dict[str, Any] = {}

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    name: str
    preferences: Dict[str, Any]
    created_at: Optional[datetime]


# ==================== PRODUCT SCHEMA ====================

class ProductBase(BaseModel):
    name: str
    category: str
    subcategory: str
    price: float
    description: str
    features: List[str] = []


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    price: Optional[float] = None
    description: Optional[str] = None
    features: Optional[List[str]] = None


class Product(ProductBase):
    id: str = Field(alias="_id", default=None)
    image_path: Optional[str] = None
    avg_rating: float = 0.0
    num_reviews: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    embedding_ids: List[str] = []

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class ProductResponse(BaseModel):
    id: str
    name: str
    category: str
    subcategory: str
    price: float
    description: str
    features: List[str]
    image_path: Optional[str]
    avg_rating: float
    num_reviews: int


# ==================== REVIEW SCHEMA ====================

class ReviewBase(BaseModel):
    product_id: str
    rating: int = Field(ge=1, le=5, default=3)
    text: str


class ReviewCreate(ReviewBase):
    pass


class Review(ReviewBase):
    id: str = Field(alias="_id", default=None)
    user_id: str
    sentiment: str = "neutral"
    sentiment_scores: Dict[str, float] = {}
    keywords: List[str] = []
    created_at: Optional[datetime] = None

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class ReviewResponse(BaseModel):
    id: str
    product_id: str
    user_id: str
    rating: int
    text: str
    sentiment: str
    sentiment_scores: Dict[str, float]
    keywords: List[str]
    created_at: Optional[datetime]


# ==================== RECOMMENDATION SCHEMA ====================

class RecommendationBase(BaseModel):
    user_id: str
    product_ids: List[str] = []
    scores: List[float] = []
    explanation: Dict[str, Any] = {}


class RecommendationCreate(RecommendationBase):
    pass


class Recommendation(RecommendationBase):
    id: str = Field(alias="_id", default=None)
    algorithm: str
    timestamp: Optional[datetime] = None

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class RecommendationResponse(BaseModel):
    id: str
    user_id: str
    product_ids: List[str]
    scores: List[float]
    explanation: Dict[str, Any]
    algorithm: str
    timestamp: Optional[datetime]


# ==================== IMAGE EMBEDDING SCHEMA ====================

class ImageEmbedding(BaseModel):
    id: str = Field(alias="_id", default=None)
    product_id: str
    embedding: List[float] = []
    model_name: str
    created_at: Optional[datetime] = None

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class ImageEmbeddingCreate(BaseModel):
    product_id: str
    embedding: List[float] = []
    model_name: str


# ==================== CHAT MESSAGE SCHEMA ====================

class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    user_id: str = "guest"
    message: str
    context: Optional[Dict[str, Any]] = {}


class ChatResponse(BaseModel):
    response: str
    relevant_products: List[Dict[str, Any]] = []
    sources: List[str] = []


# ==================== CART SCHEMA ====================

class CartItem(BaseModel):
    product_id: str
    quantity: int = 1


class CartResponse(BaseModel):
    user_id: str
    items: List[Dict[str, Any]] = []
    total: float = 0.0


# ==================== WISHLIST SCHEMA ====================

class WishlistItem(BaseModel):
    product_id: str


class WishlistResponse(BaseModel):
    user_id: str
    items: List[Dict[str, Any]] = []


# ==================== ORDER SCHEMA ====================

class OrderCreate(BaseModel):
    items: List[Dict[str, Any]] = []
    total: float = 0.0


class OrderResponse(BaseModel):
    id: str
    user_id: str
    items: List[Dict[str, Any]] = []
    total: float = 0.0
    status: str = "completed"
    created_at: Optional[datetime] = None

