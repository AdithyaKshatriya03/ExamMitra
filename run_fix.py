from database import exams_collection
import Aifetcher

print("Clearing all old hallucinated exams...")
deleted_count = exams_collection.delete_many({}).deleted_count
print(f"Deleted {deleted_count} exams.")

print("Running AI fetcher to get real active exams...")
Aifetcher.run_ai_fetch()
print("Fix completed.")
