import random
from datetime import datetime, timedelta, timezone


def generate_fireant_batch(count: int, is_news: bool = False, start_id: int = 1000, base_time: datetime | None = None) -> list[dict]:
    """
    Generates N realistic FireAnt raw JSON dictionaries.
    Timestamps are generated sequentially going backward in time from base_time.
    """
    if not base_time:
        base_time = datetime.now(timezone.utc)
        
    batch = []
    for i in range(count):
        item_id = start_id + i
        # News articles get titles; community posts do not
        title = f"Macro Economic Report {item_id}" if is_news else None
        
        batch.append({
            "postID": item_id,
            "id": item_id,
            "title": title,
            "content": f"<p>Market analysis body for item {item_id}. VN-Index <b>tăng</b>.</p>",
            "date": (base_time - timedelta(minutes=i * 10)).isoformat(),
            "taggedSymbols": [{"symbol": "VIC"}, {"symbol": "VHM"}],
            "sentiment": round(random.uniform(-1.0, 1.0), 2),
            "totalLikes": random.randint(0, 500),
            "totalShares": random.randint(0, 50),
            "creator": {"name": f"Analyst_{i}"}
        })
    return batch