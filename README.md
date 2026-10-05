# MultiModal AI Product Recommendation System

## 1. Project overview

A full-stack multimodal product recommender: FastAPI backend + MongoDB +
React/Vite frontend. It combines collaborative filtering (SVD),
content similarity (TF-IDF), review sentiment (transformer + aspect lexicon)
and sales-trend signals into one hybrid score, adds visual search
(ResNet50 + FAISS), a grounded RAG-style shopping assistant, and
per-recommendation explanations.

## 2. Problem statement

Single-signal recommenders fail on cold start, ignore review content and
product images, and cannot explain themselves. This project fuses four
signals with graceful fallbacks so every catalogue state (empty DB, new
user, new product, missing reviews/embeddings) still returns useful,
explained results.

## 3. Features

- Product search / filter / trending / categories
- Hybrid recommendations with explanations (`reasons` + `signals`)
- Similar products, frequently-bought-together
- Visual search: upload image -> similar products (FAISS), personalized re-rank
- Review sentiment + aspect analysis (battery, price, delivery, …)
- Shopping assistant chat grounded in live catalogue data (no hallucinated items)
- Auth (JWT), cart, wishlist, orders, admin analytics, customer segmentation
- Learning-to-rank re-ranker (GradientBoosting, sklearn only)

## 4. Architecture

```
                    MULTIMODAL AI PRODUCT RECOMMENDER
                                     |
        +----------------------------+----------------------------+
        v                            v                            v
 Collaborative Filtering   Computer Vision (ResNet50   NLP (transformer
 (TruncatedSVD)            2048-D -> FAISS)            sentiment + aspects)
        |                            |                            |
        +----------------------------+----------------------------+
                                     v
                          Candidate Generation
                                     v
                       Hybrid scoring (0.40/0.25/0.20/0.15)
                                     v
                    Learning-to-Rank re-rank (optional)
                                     v
                    Personalized Top-K + Explanations
                                     v
                        RAG-style Shopping Assistant
```

Request path: `app.py` (lifespan: connect MongoDB -> create indexes ->
schedule analytics in background) -> `api/*` routers -> `database.mongodb`
+ `recommendation/*` / `computer_vision/*` / `nlp/*`.

## 5. Tech stack

Backend: FastAPI, Uvicorn, Motor/PyMongo, scikit-learn, scipy, torch +
torchvision (CPU), FAISS-cpu, transformers, Pillow, OpenCV.
Frontend: React 18, Vite 5, React Router 6, MUI 5, axios.
Database: MongoDB. Tests: pytest.

## 6. Dataset

`datasets/` CSVs (sales, reviews, customer behaviour) ingested into MongoDB
via `training/ingest_to_mongodb.py`. Live catalogue: ~1000 products
(appliances), ~664 reviews (150 review users), ~351 users. All evaluation
and chat answers use the MongoDB data, not the CSVs.

> **Note:** the two raw files (`datasets/sales/sales.csv`, 180 MB and
> `datasets/reviews/reviews.csv`, 253 MB) are git-ignored because they exceed
> GitHub's 100 MB per-file limit. A fresh clone still runs fully — MongoDB
> already holds the ingested catalogue. To rebuild from scratch, drop the raw
> CSVs into `datasets/sales/` and `datasets/reviews/` and re-run
> `python training/ingest_to_mongodb.py`. Small derived files
> (`datasets/processed/*.parquet`) are committed.

## 7. Data preprocessing

`datasets/data_loader.py` + `training/preprocess_data.py`: column
normalization, price parsing, rating coercion, review text cleanup, capped
row limits for fast ingestion.

## 8. Recommendation algorithms

Baseline (weights in `config.py`, unchanged):
`score = 0.40*SVD + 0.25*content + 0.20*sentiment + 0.15*trend`.
- Collaborative: TruncatedSVD over the user-item rating matrix
  (`recommendation/collaborative_filtering.py`).
- Content: TF-IDF (1-2 grams, 5000 features) + numeric features, cosine
  (`recommendation/content_based.py`).
- Sentiment: mean positive probability per product from stored review scores.
- Trend: normalized rating x review-volume + `is_trending` flags from
  `training/sales_analytics.py` (RandomForest sales-velocity proxy).
- Cold start: popularity/trend seeding, never an empty list.

## 9. Computer vision pipeline

Upload (JPG/PNG/WEBP, <=10 MB, corruption-checked) -> ResNet50 (ImageNet
weights, 2048-D L2-normalized) -> FAISS `IndexFlatIP` -> similar products ->
optional personalized re-rank. Singleton engine (model loaded once, never
per request). Empty index / missing embeddings degrade to a popularity
fallback instead of an error. Live index: 736 vectors.

## 10. NLP pipeline

- `nlp/sentiment_analysis.py`: `cardiffnlp/twitter-roberta-base-sentiment-latest`
  via transformers pipeline, cached singleton, neutral fallback when the
  model is unavailable; rating heuristic fallback in `api/reviews.py`.
- `nlp/aspect_extraction.py`: offline lexicon (battery, quality, price,
  design, performance, size, delivery, …) + per-aspect sentiment scoring and
  product-level aggregation.
- `nlp/customer_segmentation.py`: K-Means (k=3) over spend/behaviour features.

## 11. RAG architecture

Production path is `api/chat.py` (NOT `chatbot/` — see below): intent
routing (price filter, compare, aspect reviews, purchase history, why,
similar, visual guidance, greetings) over live MongoDB queries. Every
product fact (name/price/rating) comes from the DB; out-of-domain questions
are refused with a redirect; missing data is stated explicitly.
`chatbot/` (ShoppingAssistant/VectorStore/RAGPipeline over CSV snapshots) is
kept as an offline reference implementation.

## 12. Explainable AI

Every recommendation carries `reasons[]` (only signal-backed statements),
`signals{collaborative, content, sentiment, trend}`, `sources[]`,
`signal_presence`, `is_trending`, `cold_start`, `why_recommended`
(see `HybridRecommender._explain`). Frontend renders "Why This Product?".

## 13. Learning-to-rank

`recommendation/learning_to_rank.py`: hybrid candidates -> 6 features
(collab, content, sentiment, trend, rating_norm, popularity_norm) ->
sklearn `GradientBoostingRegressor` (pointwise, no new dependencies) ->
re-ranked Top-K. Compared against the baseline on the same split (see 14).

## 14. Evaluation methodology

- Positives: review rating >= 4.
- Split: per-user random holdout of up to 2 positives (seed 42); held-out
  pairs removed from train; fit + user history use train only (no leakage).
- Metrics @K=5,10: Precision, Recall, NDCG, HitRate, MAP.
- Results (`training/eval_results.json`, 60 users):

| model    | P@10 | R@10 | NDCG@10 | HR@10 | MAP@10 |
|----------|------|------|---------|-------|--------|
| baseline | 0.0  | 0.0  | 0.0     | 0.0   | 0.0    |
| LTR      | 0.0033 | 0.0167 | 0.006 | 0.0333 | 0.0018 |

Context: HR@50 = 0.217 vs ~0.10 random; recall@100 = 0.208. The catalogue
is sparse and single-category (1000 appliances, 664 reviews), so exact
top-10 retrieval of held-out items is very hard; the model carries ~2x
random signal and LTR is marginally above baseline. Not claimed otherwise.

## 15. Actual evaluation results

See table above and `training/eval_results.json`. Reproduce with
`venv\Scripts\python.exe` running the script that writes that file
(protocol documented in its header).

## 16. Installation

```powershell
cd C:\Users\Admin\Desktop\MultiModel
.\venv\Scripts\Activate.ps1   # or: C:\Program Files\Python313\python.exe -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
venv\Scripts\python.exe -m pip install torchvision --index-url https://download.pytorch.org/whl/cpu
cd frontend; npm install
```

## 17. Environment variables (`.env`)

```
MONGODB_URL=mongodb://localhost:27017/
MONGODB_DB_NAME=multimodal_product_db
SECRET_KEY=<strong random value, required in production>
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

Frontend: `frontend/.env` with `VITE_API_URL=http://127.0.0.1:8000/api/v1`
(optional; defaults to the above).

## 18. MongoDB setup

Install MongoDB locally (default `mongodb://localhost:27017/`) or set
`MONGODB_URL` to a remote URI (`mongodb+srv://…` enables TLS automatically).
Seed: `venv\Scripts\python.exe training/ingest_to_mongodb.py`.
Image embeddings: `venv\Scripts\python.exe training/build_image_embeddings.py`.

## 19. Backend startup

```powershell
cd C:\Users\Admin\Desktop\MultiModel
C:\Program Files\Python313\python.exe run_server.py
# or: venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Startup is non-blocking: connect MongoDB -> create indexes -> serve
`/health` immediately; sales analytics + segmentation run in background.
Verify: `http://127.0.0.1:8000/health` -> `{"status":"healthy",…,"database":"connected"}`,
docs at `http://127.0.0.1:8000/docs`.

## 20. Frontend startup

```powershell
cd C:\Users\Admin\Desktop\MultiModel\frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173/`. `/api/*` is proxied to the backend (see
`frontend/vite.config.js`). Production build: `npm run build`.

## 21. API documentation

Interactive docs: `http://127.0.0.1:8000/docs`. Key routes (all under
`/api/v1`): `/auth/*`, `/products/*`, `/recommendations/*`,
`/images/search|upload|status`, `/reviews/*`, `/chat` (+`/chat/`),
`/cart/*`, `/wishlist/*`, `/orders/*`, `/admin/*`. Full matrix: 34/34
passing (see final report).

## 22. Testing

```powershell
venv\Scripts\python.exe -m pytest tests/ -q   # 18 passed
```

`tests/test_recommendation.py` (weights, cold start, explanations, metrics),
`tests/test_robustness.py` (images, FAISS-empty, aspects, sentiment
fallback), `tests/test_api_live.py` (skipped unless backend is up).

## 23. Known limitations

- Catalogue is appliances-only; laptop/phone queries are answered honestly
  as not carried.
- Offline metrics @K=10 are near zero (sparse data); relative signal
  appears at larger K (see 14).
- `chatbot/` package, `app/` config package and `api/routes.py` are unused
  legacy/duplicates (documented, harmless).
- Visual search needs `torchvision`; without it the API degrades to a
  popularity fallback.
- No refresh-token flow (24 h access tokens); frontend drops expired tokens
  and re-prompts login.

## 24. Future improvements

- Refresh tokens; full-text search index; per-user FAISS sharding;
  pairwise/listwise LTR (LightGBM) once denser interaction data exists;
  LLM-backed chat responses still constrained to retrieved catalogue facts.
