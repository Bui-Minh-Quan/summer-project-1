# Acquisition module entry point

import os 
from dotenv import load_dotenv

from connectors.fireant import FireAntConnector

from repository.mongodb import MongoRepository

from preprocessing.cleaner import DocumentCleaner
from preprocessing.validator import DocumentValidator
from preprocessing.deduplicator import DocumentDeduplicator

from services.acquisition_service import AcquisitionService

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

FIREANT_TOKEN = os.getenv("Fire_Ant_Bearer")

DATABASE = "financial_ai"

connector = FireAntConnector(bearer_token=FIREANT_TOKEN)

raw_repository = MongoRepository(
    uri=MONGO_URI,
    database=DATABASE,
    collection="raw_documents"
)

document_repository = MongoRepository(
    uri=MONGO_URI,
    database=DATABASE,
    collection="documents"
)

cleaner = DocumentCleaner()
validator = DocumentValidator()
deduplicator = DocumentDeduplicator()

service = AcquisitionService(
    connector=connector,
    raw_repository=raw_repository,
    document_repository=document_repository,
    cleaner=cleaner, 
    validator=validator,
    deduplicator=deduplicator
)


# Run

def main():

    print("=" * 60)
    print(" Financial AI Platform - Acquisition Module")
    print("=" * 60)

    if not connector.health_check():
        print("❌ FireAnt is unavailable.")
        return

    print("✅ FireAnt connection established.\n")

    report = service.backfill_news(limit=20)

    print("\nPipeline completed.\n")

    print("Processing Report")
    print("-" * 40)

    print(f"Fetched      : {report.fetched}")
    print(f"Mapped       : {report.mapped}")
    print(f"Cleaned      : {report.cleaned}")
    print(f"Invalid      : {report.invalid}")
    print(f"Duplicates   : {report.duplicates}")
    print(f"Stored       : {report.stored}")
    print(f"Duration     : {report.duration:.2f} sec")

    print("\nDone.")

    raw_repository.close()
    document_repository.close()


if __name__ == "__main__":
    main()
