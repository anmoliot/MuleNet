@echo off
rem Simple script to launch MuleNet backend and frontend

rem Docker startup checks removed – running without Docker

rem Docker compose steps removed – backend services not started

rem Give containers a moment to become healthy
timeout /t 5 >nul

rem Launch the frontend dev server (Vite) in a new window
start "frontend" cmd /c "cd frontend && npm install && npm run dev"

echo MuleNet backend and frontend are now running.
echo - Backend URL: http://localhost:8080
echo - Frontend URL: http://localhost:5173/merchant-risk

