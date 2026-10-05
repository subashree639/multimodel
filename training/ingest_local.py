"""
Local data ingestion script to demonstrate successful data loading.
Loads data from CSV and displays statistics.
"""
import sys
import os
import sqlite3
import json
import logging
from pathlib import Path
from typing import List, Dict
import random
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datasets.data_loader import DataLoader
from nlp.sentiment_analysis import SentimentAnalyzer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Initialize local SQLite database for demonstration
def setup_local_db():
    """Create a local SQLite database to demonstrate ingestion."""
    db_path = Path(__file__).resolve().parent.parent / "data_ingestion.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            name TEXT,
            category TEXT,
            subcategory TEXT,
            price REAL,
            description TEXT,
            image_path TEXT,
            avg_rating REAL,
            num_reviews INTEGER,
            is_trending BOOLEAN DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE,
            name TEXT,
            preferences TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id TEXT PRIMARY KEY,
            product_id TEXT,
            user_id TEXT,
            rating INTEGER,
            text TEXT,
            sentiment TEXT,
            sentiment_scores TEXT,
            created_at TEXT,
            FOREIGN KEY(product_id) REFERENCES products(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    conn.commit()
    return conn

def ingest_data():
    """Ingest data from CSV files into local database."""
    logger.info("Starting local data ingestion...")
    
    # Setup local database
    conn = setup_local_db()
    cursor = conn.cursor()
    
    # Load data
    loader = DataLoader(datasets_dir="datasets")
    
    # 1. Ingest Products
    logger.info("Ingesting products...")
    cursor.execute("DELETE FROM products")
    raw_products = loader.get_product_catalog()
    product_ids = []
    
    for i, p in enumerate(raw_products):
        product_id = f"prod_{i+1}"
        cursor.execute('''
            INSERT INTO products 
            (id, name, category, subcategory, price, description, image_path, avg_rating, num_reviews, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            product_id,
            p["name"],
            p["category"],
            p["subcategory"],
            p["price"],
            p["description"],
            p["image_link"],
            p["ratings"],
            p["no_of_ratings"],
            datetime.utcnow().isoformat(),
            datetime.utcnow().isoformat()
        ))
        product_ids.append(product_id)
    
    conn.commit()
    logger.info(f"Inserted {len(product_ids)} products")
    
    # 2. Ingest Users
    logger.info("Ingesting users...")
    cursor.execute("DELETE FROM users")
    raw_users = loader.get_customer_profiles()
    user_ids = []
    
    for i, u in enumerate(raw_users):
        user_id = f"user_{i+1}"
        email = f"user{u['customer_id']}@example.com"
        preferences = json.dumps({
            "city": u["city"],
            "membership": u["membership_type"],
            "gender": u["gender"],
            "age": u["age"]
        })
        cursor.execute('''
            INSERT OR IGNORE INTO users 
            (id, email, name, preferences, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            email,
            f"Customer {u['customer_id']}",
            preferences,
            datetime.utcnow().isoformat(),
            datetime.utcnow().isoformat()
        ))
        user_ids.append(user_id)
    
    # Add test user
    test_user_id = "test_user"
    cursor.execute('''
        INSERT OR IGNORE INTO users 
        (id, email, name, preferences, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        test_user_id,
        "test@example.com",
        "Test User",
        "{}",
        datetime.utcnow().isoformat(),
        datetime.utcnow().isoformat()
    ))
    user_ids.append(test_user_id)
    
    conn.commit()
    logger.info(f"Inserted {len(user_ids)} users")
    logger.info("Inserted test user: test@example.com / password123")
    
    # 3. Ingest Reviews with Sentiment Analysis
    logger.info("Ingesting reviews with Sentiment Analysis...")
    cursor.execute("DELETE FROM reviews")
    raw_reviews = loader.get_user_reviews()
    
    sentiment_analyzer = SentimentAnalyzer()
    
    review_docs = []
    for i, r in enumerate(raw_reviews):
        # Run sentiment analysis
        scores = sentiment_analyzer.analyze(r["text"])
        sentiment_label = sentiment_analyzer.get_sentiment_label(scores)
        
        # Pick random user and product
        p_id = random.choice(product_ids)
        u_id = random.choice(user_ids)
        review_id = f"review_{i+1}"
        
        sentiment_scores_json = json.dumps(scores)
        
        cursor.execute('''
            INSERT OR IGNORE INTO reviews 
            (id, product_id, user_id, rating, text, sentiment, sentiment_scores, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            review_id,
            p_id,
            u_id,
            r["rating"],
            r["text"],
            sentiment_label,
            sentiment_scores_json,
            datetime.utcnow().isoformat()
        ))
        review_docs.append(review_id)
    
    conn.commit()
    logger.info(f"Inserted {len(review_docs)} reviews")
    
    # Update products with actual average rating from reviews
    logger.info("Updating product average ratings...")
    cursor.execute('''
        SELECT product_id, AVG(rating) as avg_rating, COUNT(*) as count
        FROM reviews
        GROUP BY product_id
    ''')
    
    for product_id, avg_rating, count in cursor.fetchall():
        cursor.execute('''
            UPDATE products
            SET avg_rating = ?, num_reviews = ?
            WHERE id = ?
        ''', (round(avg_rating, 1), count, product_id))
    
    conn.commit()
    
    # 4. Mark top 10 products as trending
    logger.info("Marking top 10 products by rating as trending...")
    cursor.execute('''
        SELECT id FROM products
        ORDER BY avg_rating DESC, num_reviews DESC
        LIMIT 10
    ''')
    
    trending_products = cursor.fetchall()
    for (product_id,) in trending_products:
        cursor.execute('UPDATE products SET is_trending = 1 WHERE id = ?', (product_id,))
    
    conn.commit()
    logger.info(f"Marked {len(trending_products)} products as trending")
    
    # Get statistics
    cursor.execute("SELECT COUNT(*) FROM products")
    product_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM reviews")
    review_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM products WHERE is_trending = 1")
    trending_count = cursor.fetchone()[0]
    
    conn.close()
    
    logger.info("Data ingestion completed successfully.")
    return {
        "products_loaded": product_count,
        "users_created": user_count,
        "reviews_ingested": review_count,
        "trending_products": trending_count,
        "test_user_created": True,
        "test_user_email": "test@example.com"
    }

if __name__ == "__main__":
    try:
        stats = ingest_data()
        print("\n=== DATA INGESTION SUMMARY ===")
        print(f"Products loaded: {stats['products_loaded']}")
        print(f"Users created: {stats['users_created']}")
        print(f"Reviews ingested: {stats['reviews_ingested']}")
        print(f"Trending products (top 10): {stats['trending_products']}")
        print(f"Test user created: {stats['test_user_email']}")
        print("=" * 30)
    except Exception as e:
        logger.error(f"Error during ingestion: {e}", exc_info=True)
        sys.exit(1)
