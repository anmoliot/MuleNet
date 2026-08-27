@echo off
rem ------------------------------------------------------------
rem MuleNet – Unified launch script (Docker Compose)
rem ------------------------------------------------------------

rem Wait for Docker daemon to be ready
:waitdocker
  docker info >nul 2>&1
  if errorlevel 1 (
    echo Waiting for Docker daemon to start…
    timeout /t 2 > nul
    goto :waitdocker
  )

rem Start all services in detached mode
docker compose up -d

rem Wait a few seconds for services to become healthy
timeout /t 10 > nul

rem Open the frontend in the default browser
start "" "http://localhost:3000/merchant-risk"

rem Keep this window open so you can stop the containers later
echo MuleNet services are running. Press any key to stop them.
pause

rem Bring down the containers when you're done
docker compose down
