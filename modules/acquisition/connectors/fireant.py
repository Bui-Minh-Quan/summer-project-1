import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

import requests
from dateutil import parser
from models.document import Document, DocumentType, Language, RawDocument
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from connectors.base import BaseConnector

logger = logging.getLogger("fireant_connector")

class FireAntConnector(BaseConnector):
    # FireAnt data connector for scraping community posts and official news 
    # Convert raw API payloads into canonical Document schemas.

    BASE_URL = "https://api.fireant.vn/posts"

    def __init__(self, bearer_token: str, max_workers: int = 5):
        self.bearer_token = bearer_token 
        self.max_workers = max_workers
        self.session = self._init_session()

    @property
    def source_name(self) -> str:
        return "fireant"

    def _init_session(self) -> requests.Session:
        # Intialize an HTTP session with retry logic and standard headers.
        session = requests.Session()

        # Configure exponential backoff for server errors
        retries = Retry(
            total=5,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )

        adapter = HTTPAdapter(max_retries=retries)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        session.headers.update({
            "Authorization": f"Bearer {self.bearer_token}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        })
        return session
    
    def _polite_delay(self, min_s: float = 0.3, max_s: float = 0.8) -> None:
        # Sleep for a random interval to mimic human behavior and avoid rate limits
        time.sleep(random.uniform(min_s, max_s))

    
    def _get(self, url: str, params: dict[str, Any] | None = None) -> Any | None:
        # Wrapper for GET requests using the resilient session.
        try:
            response = self.session.get(url, params=params, timeout=15)
            if response.status_code == 200:
                return response.json()
            logger.warning(f"HTTP {response.status_code} from {url} (params: {params})")
        except Exception as e:  # noqa: BLE001
            logger.error(f"Request failed for {url}: {e!s}")
        return None


    # BaseConnector Implementations
    def health_check(self):
        # Verify API connectivity by fetching a single community post
        logger.info("Performing health check against Fireant API...")
        res = self._get(self.BASE_URL, params={"type":0, "offset":0, "limit":1})
        return isinstance(res, list) and len(res) > 0
    
    def fetch_latest_posts(
            self, limit: int = 50, since_timestamp: datetime | None = None
    ) -> list[RawDocument]:
        # Fetch newest social posts 
        # If since_timstamp is provided, it acts as a watermark and stops crawling
        # once older posts are reached 
        return self._crawl_feed(
            doc_type=DocumentType.POST,
            limit=limit,
            start_date=None,
            end_date=None,
            watermark=since_timestamp
        )
    
    def fetch_latest_news(
            self, limit: int = 50, since_timestamp: datetime | None = None
    ) -> list[RawDocument]:
        # Fetch newest official news articles using multithread detail retrieval
        return self._crawl_feed(
            doc_type=DocumentType.NEWS,
            limit=limit,
            start_date=None,
            end_date=None,
            watermark=since_timestamp
        )

    def fetch_history(self, start_date: datetime, end_date: datetime) -> list[RawDocument]:
        # Fetch all posts and news published within a specific historical time window.
        
        # Ensure UTC timezone awareness for accurate comparison
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc) 
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)

        logger.info(f"Starting historical crawl between {start_date} and {end_date}")

        posts = self._crawl_feed(
            doc_type = DocumentType.POST, 
            limit = 100000,
            start_date=start_date,
            end_date=end_date
        )

        news = self._crawl_feed(
            doc_type = DocumentType.NEWS,
            limit = 100000,
            start_date = start_date,
            end_date = end_date
        )

        return posts + news 
    
    def map_document(self, raw: RawDocument) -> Document | None:
        try: 
            # 1. Access top-level attributes using dot notation
            doc_type = raw.document_type
            doc_id = raw.id
            if not doc_id:
                return None 
        
            # 2. Extract the actual FireAnt JSON from the payload attribute
            payload = raw.payload
            
            # 3. Now use .get() on the payload dictionary
            tagged = payload.get("taggedSymbols", [])
            symbols = [
                s['symbol'] for s in tagged 
                if isinstance(s, dict) and s.get("symbol")
            ]

            # Determine content and title based on type
            title = payload.get("title")
            if doc_type == DocumentType.NEWS:
                content = payload.get("content") or payload.get("description")
            else:
                content = payload.get("originalContent") or payload.get("content")
            
            # Parse timestamp 
            pub_date = self._parse_date(payload.get("date"))

            # Isolate metadata by stripping primary keys from the payload
            primary_keys = {"postID", "id", "title", "content", "originalContent", 
                            "description", "date", "taggedSymbols"}
            metadata = {k: v for k, v in payload.items() if k not in primary_keys}

            # Enrich metadata with domain-specific metrics
            metadata["sentiment_score"] = payload.get("sentiment")
            metadata['likes'] = payload.get("totalLikes", 0)
            metadata["shares"] = payload.get("totalShares", 0)
            metadata["replies"] = payload.get("totalReplies", 0)

            return Document(
                id=doc_id,
                source=raw.source,  # Inherit from RawDocument
                url=f"https://fireant.vn/bai-viet/{doc_id}" if doc_id else None,
                title=title,
                content=content,
                raw_html=payload.get("content") if doc_type == DocumentType.NEWS else None,
                author=payload.get("creator", {}).get("name") if isinstance(payload.get("creator"), dict) else None,
                language=Language.VI,
                document_type=doc_type,
                symbols=symbols,
                published_at=pub_date,
                metadata=metadata
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Failed to map document: {e}")
            return None
        
    # Core crawling logic
    def _crawl_feed(
            self,
            doc_type: DocumentType,
            limit: int, 
            start_date: datetime | None = None,
            end_date: datetime | None = None,
            watermark: datetime | None = None
    ) -> list[RawDocument]:
        # Unified pagination loop for both posts and news
        api_type = 1 if doc_type == DocumentType.NEWS else 0
        batch_size = 500 if doc_type == DocumentType.NEWS else 1000

        offset = 0
        collected_docs: list[RawDocument] = []
        terminated = False 

        if end_date:
            offset = self._find_target_offset(api_type, end_date, batch_size)
        else:
            offset = 0

        while not terminated and len(collected_docs) < limit:
            params = {"type": api_type, "offset": offset, "limit": batch_size}
            batch = self._get(self.BASE_URL, params=params)

            if not batch:
                logger.info("Empty batch recieved or API error. Stopping crawl.")
                break 

            if doc_type == DocumentType.NEWS:
                batch_items = self._fetch_news_details(batch)
            else:
                batch_items = batch 
            batch_items.reverse()
            for raw_item in batch_items:
                if not raw_item:
                    continue

                doc_id_val = raw_item.get("postID") or raw_item.get("id")
                if not doc_id_val:
                    continue
                doc_id_str = str(doc_id_val)

                pub_date = self._parse_date(raw_item.get("date"))
                if not pub_date:
                    continue

                # 1. Check Watermark for latest fetches 
                if watermark and pub_date <= watermark:
                    logger.info(f"Reached watermark ({pub_date} <= {watermark}). Terminating.")
                    terminated = True 
                    break

                # 2. Check upper bound for historical fetches
                if end_date and pub_date > end_date:
                    # Item is too new, skip and keep paginating backward
                    continue

                # 3. Check lower bound (For historical fetches)
                if start_date and pub_date < start_date:
                    logger.info(f"Reached historical lower bound ({pub_date} < {start_date}). Terminating.")
                    terminated = True 
                    break 

                # Map to canonical schema and collect
                # doc = self._map_document(raw_item, doc_type)
                doc = RawDocument(id = doc_id_str,
                                  source="fireant",
                                  document_type=doc_type,
                                  fetched_at=datetime.now(timezone.utc),
                                  payload=raw_item)
                if doc:
                    collected_docs.append(doc)
                    if len(collected_docs) >= limit:
                        break 
            
            offset += batch_size 
            self._polite_delay()
        
        logger.info(f"Crawl completed for {doc_type.value}. Total fetched: {len(collected_docs)}")
        return collected_docs
    

    def _fetch_news_details(
            self, batch_meta: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        # Fetch full news contents concurrently given a batch of list metadata
        posts_ids = [item["postID"] for item in batch_meta if "postID" in item]
        detailed_news = []

        def _fetch_single(post_id: int) -> dict[str, Any] | None:
            time.sleep(random.uniform(0.05, 0.2))
            return self._get(f"{self.BASE_URL}/{post_id}")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_id = {executor.submit(_fetch_single, post_id): 
                                    post_id for post_id in posts_ids}
            for future in as_completed(future_to_id):
                try:
                    data = future.result()
                    if data:
                        detailed_news.append(data)
                except Exception as e:  # noqa: BLE001
                    logger.error(f"Error fetching news detail: {e}")
        
        detailed_news.sort(
            key=lambda x: self._parse_date(x.get("date")) or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True
        )
        return detailed_news
    
    # Mapping and parsing logic 
    
    def _parse_date(self, date_str: str | None) -> datetime | None:
        # Safely parse ISO date strings into UTC Datetime objects
        if not date_str:
            return None
        
        try:
            dt = parser.isoparse(date_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            
            return dt.astimezone(timezone.utc)
        except Exception as e: # noqa: BLE001
            logger.error(f"Error: {e}")
            return None
    
    def _probe_date(self, api_type: int, offset: int) -> datetime | None:
        # Lightweight probe that fetches a single item at a specific offset
        # to check its timestamp.
        res = self._get(self.BASE_URL, params={"type": api_type, "offset": offset, "limit": 1})
        if isinstance(res, list) and len(res) > 0:
            return self._parse_date(res[0].get("date"))
        
        return None

    def _find_target_offset(self, api_type: int, target_date: datetime, batch_size:int) -> int:
        # Uses Exponential search followed by binary search to locate starting offset
        # for a specific historical target_date
        logger.info(f"Probing API to find starting offset for date: {target_date.strftime('%Y-%m-%d')}...")

        # 1. Check the newest data (offset = 0)
        date_0 = self._probe_date(api_type, offset=0)
        if not date_0 or date_0 <= target_date:
            return 0
        
        # 2. Phase 1: Exponential serach to bound the upper limit
        low = 0
        high = batch_size

        while True:
            self._polite_delay(0.1, 0.3) 
            date_high = self._probe_date(api_type, offset=high)
            if not date_high or date_high <= target_date:
                break

            low = high 
            high *= 2
            logger.debug(f"Exponential leap: offset {high} (Date: {date_high.strftime('%Y-%m-%d')})")
        
        # 3. Phase 2: Binary search between [low, high]
        result_offset = low 
        while low <= high:
            mid = ((low + high) // (2 * batch_size)) * batch_size

            mid = max(mid, 0)

            self._polite_delay(0.1, 0.3)
            date_mid = self._probe_date(api_type, offset=mid)

            if not date_mid:
                # We overshot past available data, search lower half
                high = mid - batch_size
                continue
                
            if date_mid > target_date:
                # Still to new -> search deeper into the past
                low = mid + batch_size
            
            else:
                # Found the valid candidate. Try to see if we can get closer to index
                result_offset = mid 
                high = mid - batch_size

        safe_start_offset = max(0, result_offset - batch_size)
        logger.info(f"Found target window around offset {result_offset}. Starting crawl safely at offset {safe_start_offset}.")

        return safe_start_offset



        
    
