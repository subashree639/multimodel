import re
import logging
from typing import List, Optional
from pydantic import ValidationError

logger = logging.getLogger(__name__)


def validate_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_password(password: str) -> tuple[bool, str]:
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"
    return True, ""


def validate_product_name(name: str) -> bool:
    return bool(name and len(name.strip()) >= 2 and len(name) <= 200)


def validate_price(price: float) -> bool:
    return isinstance(price, (int, float)) and price >= 0 and price < 1_000_000


def validate_rating(rating: float) -> bool:
    return isinstance(rating, (int, float)) and 1 <= rating <= 5


def validate_review_text(text: str) -> bool:
    return bool(text and len(text.strip()) >= 3 and len(text) <= 5000)


def sanitize_string(text: str, max_length: int = 1000) -> str:
    text = re.sub(r'[<>{}[\]\\]', '', text)
    return text.strip()[:max_length]

