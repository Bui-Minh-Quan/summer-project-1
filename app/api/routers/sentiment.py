
from fastapi import APIRouter, Query, Request
from fastapi_cache.decorator import cache
from pydantic import BaseModel

router = APIRouter()

class NewsRecord(BaseModel):
    id: str
    title: str
    content: str
    published_at: str
    source: str
    url: str | None

class SentimentScore(BaseModel):
    symbol: str
    positive_count: int
    negative_count: int
    neutral_count: int
    total_engagement: int
    normalized_hype_score: float

@router.get("/news/{symbol}", response_model=list[NewsRecord])
@cache(expire=300)
async def get_related_news(
    symbol: str, 
    request: Request, 
    page: int = Query(1, ge=1), 
    limit: int = Query(20, ge=1, le=50)
):
    """Feature 5: Paginated related news query."""
    db = request.app.state.db
    skip = (page - 1) * limit
    
    # Filter strictly for news targeting the requested ticker
    query = {
        "document_type": "news",
        "symbols": symbol
    }
    
    cursor = db["documents"].find(query).sort("published_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    
    results = []
    for doc in docs:
        results.append(NewsRecord(
            id=doc.get("id", ""),
            title=doc.get("title", "Untitled"),
            # Truncate content for a cleaner UI preview
            content=doc.get("content", "")[:250] + "...", 
            published_at=str(doc.get("published_at")),
            source=doc.get("source", "Unknown"),
            url=doc.get("url")
        ))
    return results


@router.get("/score/{symbol}", response_model=SentimentScore)
@cache(expire=300)
async def get_social_sentiment(symbol: str, request: Request):
    """Feature 7: Dynamic social sentiment aggregation."""
    db = request.app.state.db
    
    # MongoDB Aggregation Pipeline to compute counts on the fly
    pipeline = [
        {"$match": {"document_type": "post", "symbols": symbol}},
        {"$group": {
            "_id": "$symbols",
            "total_posts": {"$sum": 1},
            "positive_count": {
                "$sum": {"$cond": [{"$gt": ["$metadata.sentiment", 0]}, 1, 0]}
            },
            "negative_count": {
                "$sum": {"$cond": [{"$lt": ["$metadata.sentiment", 0]}, 1, 0]}
            },
            "neutral_count": {
                "$sum": {"$cond": [{"$eq": ["$metadata.sentiment", 0]}, 1, 0]}
            },
            "total_likes": {"$sum": "$metadata.likes"},
            "total_shares": {"$sum": "$metadata.shares"},
            "total_replies": {"$sum": "$metadata.replies"}
        }}
    ]
    
    result = await db["documents"].aggregate(pipeline).to_list(length=1)
    
    if not result:
        # Fallback if no posts exist for the symbol
        return SentimentScore(
            symbol=symbol, positive_count=0, negative_count=0, 
            neutral_count=0, total_engagement=0, normalized_hype_score=0.0
        )
        
    data = result[0]
    engagement = data.get("total_likes", 0) + data.get("total_shares", 0) + data.get("total_replies", 0)
    pos = data.get("positive_count", 0)
    neg = data.get("negative_count", 0)
    
    # Hype score formula (prevent division by zero)
    hype_score = (pos - neg) / max(engagement, 1)
    
    return SentimentScore(
        symbol=symbol,
        positive_count=pos,
        negative_count=neg,
        neutral_count=data.get("neutral_count", 0),
        total_engagement=engagement,
        normalized_hype_score=round(hype_score, 4)
    )
