#!/bin/bash
set -e

echo "Starting InterviewPilot development environment..."

# Parse args
TAURI_MODE=false
if [[ "$1" == "--tauri" ]] || [[ "$1" == "-t" ]]; then
    TAURI_MODE=true
fi

# Start Ollama (if not running)
if ! pgrep -x "ollama" > /dev/null; then
    echo "Starting Ollama..."
    ollama serve &>/dev/null &
    sleep 2
fi

# Start backend
echo "Starting Python backend on :8000..."
cd backend
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

if [ "$TAURI_MODE" = true ]; then
    # Tauri mode: let Tauri manage the frontend
    echo "Starting Tauri desktop app..."
    cd ../src-tauri
    cargo tauri dev &
    TAURI_PID=$!

    echo ""
    echo "================================================"
    echo "  InterviewPilot Desktop App is running!"
    echo "  Backend:  http://localhost:8000"
    echo "  API Docs: http://localhost:8000/docs"
    echo "  Press Ctrl+C to stop."
    echo "================================================"

    trap "kill $BACKEND_PID $TAURI_PID 2>/dev/null; exit" SIGINT SIGTERM
    wait
else
    # Web mode: start frontend dev server
    echo "Starting React frontend on :5173..."
    cd ../frontend
    npm run dev &
    FRONTEND_PID=$!

    echo ""
    echo "================================================"
    echo "  InterviewPilot is running!"
    echo "  Frontend: http://localhost:5173"
    echo "  Backend:  http://localhost:8000"
    echo "  API Docs: http://localhost:8000/docs"
    echo ""
    echo "  For desktop app mode: ./scripts/dev.sh --tauri"
    echo "  Press Ctrl+C to stop."
    echo "================================================"

    trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM
    wait
fi
