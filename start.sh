#!/bin/bash
# Apply schema
python -m app.init_db
# Start FastAPI application
uvicorn app.main:app --host 0.0.0.0 --port $PORT
