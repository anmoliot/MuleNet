@echo off
rem Simple script to launch MuleNet backend (Docker) and your frontend (HCL Tech) together

rem ----- Check Docker -----
docker info >nul 2>&1
if errorlevel 1 (
    echo Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)

rem ----- Start backend services (Docker Compose) -----
pushd "C:\Users\Anmol\OneDrive\Desktop\MuleNet"
docker compose up -d backend ml_service
if %errorlevel% neq 0 (
    echo Failed to start backend containers.
    popd
    pause
    exit /b 1
)
popd

rem ----- Give containers a moment to become healthy -----
timeout /t 5 >nul

rem ----- Launch the frontend dev server (your HCL Tech UI) -----
start "frontend" cmd /c "cd /d C:\Users\Anmol\Desktop\HCL Tech && npm install && npm run dev"

echo.
echo MuleNet backend is running at http://localhost:8080
echo Frontend (HCL Tech) is running at http://localhost:5173/merchant-risk
echo.
echo Press any key to stop backend containers (Docker) and close this window.
pause

rem ----- Stop backend containers when done -----
pushd "C:\Users\Anmol\OneDrive\Desktop\MuleNet"
docker compose down
popd
