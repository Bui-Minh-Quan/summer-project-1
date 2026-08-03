"""
Data Extractor for Module 4 MLOps Pipeline.
Exports feature records from MongoDB into a DVC-tracked Parquet file.
"""

import logging
import sys
from pathlib import Path

import pandas as pd
from pymongo import MongoClient

from modules.mlops.config import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("mlops_data_extractor")


def extract_gold_features(output_path: Path | None = None) -> Path:
    """Fetches all records from gold_market_features collection and saves to Parquet."""
    destination = output_path or config.parquet_path
    
    logger.info(f"Connecting to MongoDB database '{config.db_name}'...")
    client: MongoClient = MongoClient(config.mongo_uri)
    db = client[config.db_name]
    collection = db[config.collection_name]
    
    # Fetch all records excluding MongoDB internal `_id`
    logger.info(f"Querying collection '{config.collection_name}'...")
    cursor = collection.find({}, {"_id": 0})
    records = list(cursor)
    client.close()
    
    if not records:
        logger.warning("⚠️ No records found in MongoDB gold_market_features collection!")
        return destination

    df = pd.DataFrame(records)
    
    # Ensure datetime formatting and proper sorting
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.sort_values(by=["symbol", "timestamp"]).reset_index(drop=True)

    # Save to Parquet using pyarrow engine
    df.to_parquet(destination, engine="pyarrow", index=False)
    logger.info(
        f"✅ Exported {len(df)} feature rows for {df['symbol'].nunique()} symbols to '{destination}'"
    )
    
    return destination


if __name__ == "__main__":
    extract_gold_features()