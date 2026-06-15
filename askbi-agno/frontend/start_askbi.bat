@echo off
echo Installing dependencies...
pip install fastapi uvicorn httpx python-multipart

echo.
echo Building frontend...
call npm install
call npm run build

echo.
echo Starting AskBI Proxy Server...
echo Please open http://localhost:8000 in your browser
echo.
python proxy_server.py
pause

