"""
Review text preprocessing utilities.
"""

import re
import string
import logging
from typing import List, Dict
from collections import Counter
import numpy as np
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer

logger = logging.getLogger(__name__)

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('tokenizers/punkt_tab')
    nltk.data.find('corpora/stopwords')
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('wordnet', quiet=True)
    nltk.download('punkt_tab', quiet=True)


class ReviewPreprocessor:
    """Preprocesses product review text for NLP analysis."""

    def __init__(self, remove_stopwords: bool = True, lemmatize: bool = True):
        """
        Initialize the review preprocessor.

        Args:
            remove_stopwords: Whether to remove stop words
            lemmatize: Whether to lemmatize tokens
        """
        self.remove_stopwords = remove_stopwords
        self.lemmatize = lemmatize
        self.stopwords = set(stopwords.words('english'))
        self.lemmatizer = WordNetLemmatizer()
        self.punctuation_table = str.maketrans('', '', string.punctuation)

    def clean_text(self, text: str) -> str:
        """
        Basic text cleaning: lowercase, remove special chars, URLs.

        Args:
            text: Raw review text

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        # Lowercase
        text = text.lower()

        # Remove URLs
        text = re.sub(r'http\S+', '', text)
        text = re.sub(r'www\.\S+', '', text)

        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        # Remove special characters that aren't punctuation
        text = re.sub(r'[^\w\s\.\,\!\?]', '', text)

        return text

    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into words.

        Args:
            text: Input text

        Returns:
            List of tokens
        """
        tokens = word_tokenize(text)
        return tokens

    def preprocess(self, text: str) -> str:
        """
        Full preprocessing pipeline.

        Args:
            text: Raw review text

        Returns:
            Preprocessed text string
        """
        if not text:
            return ""

        # Clean
        text = self.clean_text(text)

        # Tokenize
        tokens = self.tokenize(text)

        # Remove punctuation and stopwords, lemmatize
        processed = []
        for token in tokens:
            # Remove punctuation
            token = token.translate(self.punctuation_table)
            if not token:
                continue

            # Remove numbers-only tokens
            if token.isdigit():
                continue

            # Remove stopwords
            if self.remove_stopwords and token in self.stopwords:
                continue

            # Lemmatize
            if self.lemmatize:
                token = self.lemmatizer.lemmatize(token)

            processed.append(token)

        return ' '.join(processed)

    def preprocess_batch(self, texts: List[str]) -> List[str]:
        """
        Preprocess a batch of texts.

        Args:
            texts: List of raw texts

        Returns:
            List of preprocessed texts
        """
        return [self.preprocess(text) for text in texts]

    def extract_keywords(self, text: str, top_k: int = 5) -> List[str]:
        """
        Extract top keywords from text using frequency analysis.

        Args:
            text: Input text
            top_k: Number of keywords to return

        Returns:
            List of top keywords
        """
        processed = self.preprocess(text)
        tokens = processed.split()

        # Count frequencies
        freq = Counter(tokens)

        # Remove very short and very long words
        filtered = {
            word: count for word, count in freq.items()
            if 3 <= len(word) <= 20
        }

        # Get top keywords
        keywords = [word for word, _ in Counter(filtered).most_common(top_k)]
        return keywords

    def get_text_length_stats(self, texts: List[str]) -> Dict:
        """
        Compute text length statistics.

        Args:
            texts: List of review texts

        Returns:
            Dictionary of stats
        """
        lengths = [len(text.split()) for text in texts if text]
        if not lengths:
            return {'mean': 0, 'median': 0, 'max': 0, 'min': 0}

        return {
            'mean': float(np.mean(lengths)),
            'median': float(np.median(lengths)),
            'max': int(max(lengths)),
            'min': int(min(lengths)),
            'total_words': sum(lengths)
        }

    def filter_by_length(self, texts: List[str], min_words: int = 3, max_words: int = 500) -> List[str]:
        """
        Filter texts by word count.

        Args:
            texts: List of texts
            min_words: Minimum word count
            max_words: Maximum word count

        Returns:
            Filtered list of texts
        """
        filtered = []
        for text in texts:
            word_count = len(text.split())
            if min_words <= word_count <= max_words:
                filtered.append(text)
        return filtered
