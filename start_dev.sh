#!/bin/bash

# Text colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting Context Compression System in development mode...${NC}\n"

# Start backend service
echo "Starting backend service..."
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000 &

# Wait a moment for backend to initialize
sleep 3

# Start frontend service
echo -e "\nStarting frontend service..."
cd ../frontend/context-compression-frontend
npm install
npm run dev &

# Print access information
echo -e "\n${GREEN}✅ Services are starting up!${NC}"
echo -e "\n${BLUE}Access the application at:${NC}"
echo "Frontend: http://localhost:5173"  # Vite's default port
echo "Backend API: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"

echo -e "\n${BLUE}Press Ctrl+C to stop all services${NC}"

# Wait for user interrupt
wait
