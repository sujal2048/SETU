import json
import asyncio
import httpx
from pathlib import Path

API_URL = "http://localhost:8000"

async def ingest_events():
    events_file = Path(__file__).parent.parent / "sample_events.json"
    with open(events_file, "r") as f:
        events = json.load(f)
        
    print(f"Loaded {len(events)} events. Starting ingestion...")
    
    async with httpx.AsyncClient(base_url=API_URL, timeout=30.0) as client:
        # We can ingest in batches for speed, but sequentially is safer to test the API correctly
        success = 0
        ignored = 0
        failed = 0
        
        # Batching requests to speed up ingestion
        chunk_size = 100
        for i in range(0, len(events), chunk_size):
            chunk = events[i:i+chunk_size]
            tasks = [client.post("/events", json=event) for event in chunk]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            for response in responses:
                if isinstance(response, Exception):
                    failed += 1
                    continue
                
                if response.status_code == 201:
                    res = response.json()
                    if res.get("status") == "success":
                        success += 1
                    else:
                        ignored += 1
                else:
                    failed += 1
            print(f"Processed {min(i+chunk_size, len(events))}/{len(events)} events...")
                
        print(f"Ingestion complete!")
        print(f"Success: {success}")
        print(f"Ignored (Duplicates): {ignored}")
        print(f"Failed: {failed}")

if __name__ == "__main__":
    asyncio.run(ingest_events())
