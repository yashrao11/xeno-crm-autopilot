#!/bin/bash

# 1. Run database migrations/seeding on startup
python scripts/seed_db.py

# 2. Start the Channel Stub service in the background on port 8001
python -m uvicorn channel_stub.main:app --host 127.0.0.1 --port 8001 &

# 3. Start the main CRM Application in the foreground on the dynamic Render port
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT