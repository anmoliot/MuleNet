@echo off
set JAVA_HOME=C:\Program Files\Java\jdk-25
rem ------------------------------------------------------------
rem MuleNet – Unified launch script (Windows batch)
rem ------------------------------------------------------------

rem 1. Ensure PostgreSQL is running (user must start PostgreSQL manually or via Docker)
rem    Default connection: user=postgres, password=postgres, database=mulenet

rem 2. Start Spring Boot backend
start "Backend" cmd /k "cd /d %~dp0backend && mvnw.cmd spring-boot:run"

rem Wait a few seconds for the backend to spin up
timeout /t 5 > nul

rem 3. Start Python FastAPI ML service
start "ML Service" cmd /k "cd /d %~dp0ml_service && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

rem Wait a few seconds for the ML service to be ready
timeout /t 5 > nul

rem 4. Install frontend dependencies (only the first run) and start Vite dev server
cd /d %~dp0frontend
if not exist node_modules (npm install)
start "Frontend" cmd /k "npm run dev"
