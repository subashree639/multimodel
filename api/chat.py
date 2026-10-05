"""RAG shopping assistant backed by real MongoDB product/review data.

Supports: price filters (₹), similar items, aspect (battery) reviews,
purchase-history recs, why-explanations, compare, visual-search guidance.
Never invents names/prices/ratings — every fact comes from the DB; when
information is unavailable the assistant says so explicitly.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

from api.serializers import serialize_product
from database.mongodb import db_manager

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    user_id: str = "guest"
    message: str
    context: dict = {}


class ChatResponse(BaseModel):
    response: str
    relevant_products: List[dict] = []
    sources: List[str] = []


def _try_oid(value: str):
    try:
        from bson import ObjectId
        return ObjectId(value)
    except Exception:
        return None


def _fmt(p: Dict) -> str:
    return f"{p.get('name','Unnamed')} (₹{p.get('price',0):,.0f}, {p.get('avg_rating',0)}/5, {p.get('num_reviews',0)} reviews)"


_STOPWORDS = frozenset("""
    what which who whom whose where when why how is are was were be been being
    the a an of to in on for and or with tell about this that these those
    does do did have has had it its as at by from me my you your we our
    please kind show get give there here than then so such no not any all
    can could would should will just like want need look see know than
""".split())


async def _search_products(db, text: str, limit: int = 5) -> List[Dict]:
    raw_words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    # Drop stopwords and pure numbers ("the", "99") so generic/out-of-domain
    # queries cannot match the catalogue on filler tokens.
    words = [w for w in raw_words if len(w) > 2 and w not in _STOPWORDS and not w.isdigit()][:6]
    if not words:
        return []
    ors = []
    for w in words:
        ors.append({"name": {"$regex": re.escape(w), "$options": "i"}})
        ors.append({"category": {"$regex": re.escape(w), "$options": "i"}})
        ors.append({"description": {"$regex": re.escape(w), "$options": "i"}})
    cur = db.products.find({"$or": ors}).limit(limit * 3)
    docs = [serialize_product(p) async for p in cur]
    # Rank: more word hits + higher rating first.
    def _score(d):
        blob = f"{d.get('name','')} {d.get('category','')} {d.get('description','')}".lower()
        hits = sum(1 for w in words if w in blob)
        return (hits, float(d.get("avg_rating") or 0))
    docs.sort(key=_score, reverse=True)
    # Drop zero-hit matches: a regex hit on an unrelated token must not be
    # presented as an answer (e.g. "capital of France" -> kitchen scales).
    kept = []
    for d in docs:
        if _score(d)[0] >= 1:
            kept.append(d)
        if len(kept) >= limit:
            break
    return kept


_OOD_PATTERNS = [
    r"\bcapital of\b", r"\bpresident\b", r"\bprime minister\b", r"\bcountry\b",
    r"\bweather\b", r"\bwho (is|was|won|discovered|invented)\b",
    r"\btranslate\b", r"\bsolve\b", r"\bequation\b",
    r"\btell me a (joke|poem|story)\b", r"\bwrite (code|a poem|an essay)\b",
]
_SHOPPING_HINTS = frozenset("""
    price cost cheap budget buy order purchase recommend recommends recommended
    recommending suggestion suggest suggests suggested explain explains explanation
    similar compare review rating battery product laptop phone tv tablet watch camera headphone
    brand category delivery return warranty discount offer deal search find show
    looking versus vs shopping store trending popular history favourite favorite
""".split())
_QUESTION_START = re.compile(r"^\s*(what|who|whom|whose|where|when|why|how|is|are|was|were|can|could|do|does|did)\b", re.I)


def _is_out_of_domain(low: str) -> bool:
    if any(re.search(p, low) for p in _OOD_PATTERNS):
        return True
    if "?" in low or _QUESTION_START.match(low):
        tokens = set(re.findall(r"[a-z]+", low))
        if not (tokens & _SHOPPING_HINTS):
            return True
    return False


_CATEGORY_TOKENS = ("laptop", "smartphone", "tablet", "television", "camera")


async def _missing_category_note(db, low: str) -> str:
    """If the user names a product category we don't carry, say so explicitly."""
    for tok in _CATEGORY_TOKENS:
        if tok in low:
            n = await db.products.count_documents({
                "$or": [{"category": {"$regex": tok, "$options": "i"}},
                        {"name": {"$regex": tok, "$options": "i"}}]
            })
            if n == 0:
                return tok
    if "phone" in low and "headphone" not in low and "smartphone" not in low:
        n = await db.products.count_documents({
            "$or": [{"category": {"$regex": "phone", "$options": "i"}},
                    {"name": {"$regex": "smartphone|mobile phone", "$options": "i"}}]
        })
        if n == 0:
            return "phone"
    return ""


async def _handle(db, message: str, user_id: str) -> Dict[str, Any]:
    msg = message.strip()
    low = msg.lower()
    products: List[Dict] = []
    sources: List[str] = []

    # 0. Out-of-domain: refuse/redirect, never fake catalogue matches.
    if _is_out_of_domain(low):
        return {"response": ("I'm a shopping assistant for this store — I can't answer general-knowledge "
                             "questions. I can help you find products, compare catalogue items, check prices, "
                             "look at reviews (e.g. battery feedback), or explain recommendations. What are you shopping for?"),
                "products": [], "sources": []}

    # 1. Price filter: "laptops under ₹70000" / "under 70000"
    m = re.search(r"under\s*[₹$]?\s*([\d,]+)", low)
    if m and any(w in low for w in ("laptop", "phone", "tv", "product", "find", "under", "budget", "cheap")):
        budget = float(m.group(1).replace(",", ""))
        cat = None
        for c in ("laptop", "phone", "headphone", "camera", "tv", "watch", "tablet"):
            if c in low:
                cat = c
                break
        q: Dict[str, Any] = {"price": {"$lte": budget}}
        if cat:
            q["$or"] = [{"category": {"$regex": cat, "$options": "i"}},
                        {"name": {"$regex": cat, "$options": "i"}}]
        cur = db.products.find(q).sort("price", 1).limit(5)
        products = [serialize_product(p) async for p in cur]
        if not products:
            return {"response": f"I checked the catalogue and found no products under ₹{budget:,.0f} matching your query. Try a higher budget or a different category.",
                    "products": [], "sources": []}
        lines = "\n".join(f"{i+1}. {_fmt(p)}" for i, p in enumerate(products))
        return {"response": f"Here are products under ₹{budget:,.0f} from our catalogue:\n{lines}",
                "products": products, "sources": [f"Product: {p['name']} (ID: {p['id']})" for p in products]}

    # 2. Compare two products: "compare A and B" / "compare X vs Y"
    if any(w in low for w in ("compare", " vs ", " versus ", "difference between")):
        hits = await _search_products(db, msg, limit=2)
        query_words = {w for w in re.findall(r"[a-z0-9]+", low) if len(w) > 3}

        def _relates(p: Dict) -> bool:
            blob = f"{p.get('name','')} {p.get('category','')} {p.get('subcategory','')}".lower()
            return any(w in blob for w in query_words)

        related = [h for h in hits if _relates(h)]
        if len(related) >= 2:
            a, b = related[0], related[1]
            return {"response": (f"Comparing from catalogue data:\n- {a['name']}: ₹{a.get('price',0):,.0f}, rating {a.get('avg_rating',0)}/5 ({a.get('num_reviews',0)} reviews)\n"
                                 f"- {b['name']}: ₹{b.get('price',0):,.0f}, rating {b.get('avg_rating',0)}/5 ({b.get('num_reviews',0)} reviews)\n"
                                 f"Both are in {a.get('category','?')} / {b.get('category','?')}. Prices and ratings are live catalogue values."),
                    "products": [a, b], "sources": [f"Product: {p['name']} (ID: {p['id']})" for p in (a, b)]}
        return {"response": ("I can only compare products we actually carry — please name two of them, "
                             "e.g. 'compare <product A> and <product B>', or browse the catalogue for available items."),
                "products": [], "sources": []}

    # 3. Battery / aspect reviews: "good battery"
    if "battery" in low and any(w in low for w in ("good", "best", "review", "battery")):
        cur = db.reviews.find({"aspect_sentiments.battery.positive": {"$gte": 0.5}}).limit(20)
        good_pids = set()
        async for r in cur:
            good_pids.add(r.get("product_id", ""))
        plist = []
        for pid in list(good_pids)[:5]:
            oid = _try_oid(pid)
            p = await db.products.find_one({"_id": oid}) if oid else None
            if p:
                plist.append(serialize_product(p))
        if not plist:
            # fallback: products whose reviews mention battery at all
            cur2 = db.reviews.find({"text": {"$regex": "battery", "$options": "i"}}).limit(20)
            pids2 = set()
            async for r in cur2:
                pids2.add(r.get("product_id", ""))
            for pid in list(pids2)[:5]:
                oid = _try_oid(pid)
                p = await db.products.find_one({"_id": oid}) if oid else None
                if p:
                    plist.append(serialize_product(p))
        if not plist:
            return {"response": "I don't have battery-review data for any product right now, so I can't rank by battery. Try asking about a specific product's reviews.",
                    "products": [], "sources": []}
        lines = "\n".join(f"{i+1}. {_fmt(p)}" for i, p in enumerate(plist))
        prefix = ""
        missing = await _missing_category_note(db, low)
        if missing:
            prefix = (f"Note: our catalogue doesn't carry {missing}s (it's appliances-focused), "
                      f"so I can't name a {missing} model. ")
        return {"response": f"{prefix}Products with good battery mentions in real reviews:\n{lines}\n(Scores come from stored aspect sentiment, not guesses.)",
                "products": plist, "sources": [f"Product: {p['name']} (ID: {p['id']})" for p in plist]}

    # 4. Purchase-history recs
    if any(w in low for w in ("previous purchase", "purchase history", "based on my", "bought before", "my orders")):
        if user_id in ("guest", "", None):
            return {"response": "I don't see any purchase history for a guest profile. Log in so I can base recommendations on your real orders.",
                    "products": [], "sources": []}
        hist: List[str] = []
        async for o in db.orders.find({"user_id": user_id}, {"items": 1}):
            for it in o.get("items", []):
                if it.get("product_id") and it["product_id"] not in hist:
                    hist.append(it["product_id"])
        if not hist:
            return {"response": "I found no past orders for your account, so I can't personalize from purchases yet. Tell me a category you like and I'll suggest popular items.",
                    "products": [], "sources": []}
        # Recommend same-category items not already bought.
        last = await db.products.find_one({"_id": _try_oid(hist[-1])}) if _try_oid(hist[-1] or "") else None
        cat = (last or {}).get("category", "")
        q = {"_id": {"$nin": [o for o in map(_try_oid, hist) if o]}}
        if cat:
            q["category"] = cat
        cur = db.products.find(q).sort([("avg_rating", -1)]).limit(5)
        products = [serialize_product(p) async for p in cur]
        lines = "\n".join(f"{i+1}. {_fmt(p)}" for i, p in enumerate(products))
        return {"response": f"Based on your {len(hist)} previously purchased item(s) (same category: {cat or 'mixed'}):\n{lines}",
                "products": products, "sources": [f"Product: {p['name']} (ID: {p['id']})" for p in products]}

    # 5. Why recommending / explanation
    if low.startswith("why") and ("recommend" in low or "suggest" in low or "this" in low):
        return {"response": ("Every recommendation shows its real signals: collaborative (similar users), content similarity, "
                             "review sentiment and sales trend, e.g. signals {collaborative, content, sentiment, trend}. "
                             "Open any recommendation's explanation to see the exact scores — I never invent reasons."),
                "products": [], "sources": []}

    # 6. Visual / image query (before similar-product matching: "similar to
    # this uploaded image" is a visual request, not a catalogue reference).
    if any(w in low for w in ("uploaded image", "upload image", "image search", "visual search", "similar to this image", "photo")):
        return {"response": ("To find products similar to an image, use POST /api/v1/images/search with the image file "
                             "(JPG/PNG/WEBP). I return visually similar catalogue items with similarity scores, re-ranked for you when you pass user_id."),
                "products": [], "sources": []}

    # 7. Similar to product id
    m = re.search(r"similar to ([0-9a-f]{24})", low)
    if m or ("similar" in low and ("this" in low or "product" in low)):
        pid = m.group(1) if m else None
        if pid is None:
            # try to resolve a product name from the message
            hits = await _search_products(db, msg, limit=1)
            if hits:
                pid = hits[0]["id"]
        if pid:
            try:
                from recommendation.hybrid_recommender import HybridRecommender  # lazy
                from api.recommendations import _ensure_fitted
                await _ensure_fitted(db)
                from api.recommendations import recommender
                pairs = recommender.get_similar_products(pid, top_n=5)
                plist = []
                for spid, score in pairs:
                    p = await db.products.find_one({"_id": _try_oid(spid)})
                    if p:
                        plist.append(serialize_product(p))
                if plist:
                    lines = "\n".join(f"{i+1}. {_fmt(p)}" for i, p in enumerate(plist))
                    return {"response": f"Products similar to {pid} (content similarity):\n{lines}",
                            "products": plist, "sources": [f"Product: {p['name']} (ID: {p['id']})" for p in plist]}
            except Exception as e:
                logger.debug(f"similar lookup failed: {e}")
        return {"response": "I couldn't resolve which product you mean. Please paste a product ID from the catalogue.", "products": [], "sources": []}

    # 8. Greetings
    if re.search(r"\b(hi|hello|hey|good morning|good evening)\b", low):
        return {"response": "Hello! I'm your shopping assistant. Ask me e.g. 'Find laptops under ₹70000' or 'Which products have good battery reviews?'",
                "products": [], "sources": []}
    if re.search(r"\b(bye|goodbye|see you)\b", low):
        return {"response": "Goodbye! Come back anytime for shopping help.", "products": [], "sources": []}

    # 9. Default: keyword product search over real catalogue.
    products = await _search_products(db, msg, limit=5)
    if not products:
        return {"response": "I searched the catalogue and found no matching products. Could you rephrase or give a category/price range? I won't guess items we don't carry.",
                "products": [], "sources": []}
    lines = "\n".join(f"{i+1}. {_fmt(p)}" for i, p in enumerate(products))
    return {"response": f"Based on catalogue matches:\n{lines}\nWant details or a comparison of any of these?",
            "products": products, "sources": [f"Product: {p['name']} (ID: {p['id']})" for p in products]}


@router.post("/")
async def chat(req: ChatRequest, request: Request):
    return await _respond(req)


@router.post("")
async def chat_no_slash(req: ChatRequest, request: Request):
    """Alias so /api/v1/chat (no trailing slash) also works."""
    return await _respond(req)


async def _respond(req: ChatRequest):
    message = (req.message or "").strip()
    if not message:
        return {"response": "Please enter a message.", "relevant_products": [], "sources": []}
    try:
        db = db_manager.get_async_db()
    except Exception as e:
        logger.error(f"Chat DB unavailable: {e}")
        return {"response": "Product data is currently unavailable, so I can't look anything up. Please try again later.",
                "relevant_products": [], "sources": []}
    try:
        out = await _handle(db, message, req.user_id or "guest")
        prods = out["products"][:5]
        return {"response": out["response"], "relevant_products": prods, "sources": out.get("sources", [])[:5]}
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        return {"response": "Sorry, something went wrong looking up products. Please try again.",
                "relevant_products": [], "sources": []}
