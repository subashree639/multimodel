import re
import logging
from typing import List, Dict, Tuple
from collections import Counter

import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

logger = logging.getLogger(__name__)

EXTRA_STOPWORDS = {
    "product", "products", "buy", "bought", "purchase", "purchased", "use", "used", "using",
    "item", "items", "good", "bad", "great", "nice", "ok", "okay", "worth", "quality",
    "like", "really", "would", "could", "also", "much", "many", "well", "make", "made",
    "get", "got", "think", "thing", "things", "recommend", "recommended", "definitely",
    "absolutely", "one", "two", "new", "old", "time", "times",
}


class KeywordExtractor:
    def __init__(self, method: str = "tfidf"):
        self.method = method
        self.stopwords = self._load_stopwords()

    def _load_stopwords(self):
        try:
            from nltk.corpus import stopwords as nltk_stopwords
            sw = set(nltk_stopwords.words("english")) | EXTRA_STOPWORDS
        except Exception:
            sw = set(EXTRA_STOPWORDS)
        for resource in ("tokenizers/punkt", "tokenizers/punkt_tab"):
            try:
                nltk.data.find(resource)
            except LookupError:
                nltk.download(resource.split("/")[-1], quiet=True)
        return sw

    def clean_text(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r"http\S+", "", text)
        text = re.sub(r"[^\w\s]", " ", text)
        text = re.sub(r"\d+", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def extract_keywords(self, reviews: List[str], top_k: int = 10) -> List[Tuple[str, float]]:
        if not reviews:
            return []
        cleaned = [self.clean_text(r) for r in reviews if r]
        if not cleaned:
            return []
        if self.method == "tfidf":
            return self._extract_tfidf(cleaned, top_k)
        return self._extract_frequency(cleaned, top_k)

    def _extract_tfidf(self, texts: List[str], top_k: int) -> List[Tuple[str, float]]:
        try:
            vectorizer = TfidfVectorizer(stop_words=list(self.stopwords), max_features=500, ngram_range=(1, 2), min_df=1)
            matrix = vectorizer.fit_transform(texts)
            mean_scores = np.mean(matrix.toarray(), axis=0)
            names = vectorizer.get_feature_names_out()
            idx = np.argsort(mean_scores)[::-1][:top_k]
            return [(names[i], float(mean_scores[i])) for i in idx if mean_scores[i] > 0]
        except Exception as e:
            logger.error(f"TF-IDF error: {e}")
            return self._extract_frequency(texts, top_k)

    def _extract_frequency(self, texts: List[str], top_k: int) -> List[Tuple[str, float]]:
        words = []
        for text in texts:
            tokens = word_tokenize(text.lower())
            words.extend([t for t in tokens if t not in self.stopwords and len(t) > 2 and t.isalpha()])
        counter = Counter(words)
        return counter.most_common(top_k)

    def extract_single_keywords(self, review: str, top_k: int = 5) -> List[str]:
        if not review:
            return []
        cleaned = self.clean_text(review)
        results = self._extract_frequency([cleaned], top_k * 2)
        return [word for word, _ in results if len(word.split()) == 1][:top_k]

    def get_review_summary(self, review: str) -> str:
        keywords = self.extract_single_keywords(review, top_k=3)
        return f"Key aspects: {', '.join(keywords)}" if keywords else "Review analyzed"
