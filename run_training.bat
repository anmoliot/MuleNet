@echo off

:: ------------------------------------------------------------
:: 1 Activate the Python virtual environment (if exists)
:: ------------------------------------------------------------
if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
) else (
    echo [WARNING] No virtual environment found. Using system Python.
)

:: ------------------------------------------------------------
:: 2 Install project dependencies
:: ------------------------------------------------------------
pip install -q -r ml_service\requirements.txt

:: ------------------------------------------------------------
:: 3 Set environment variables
:: ------------------------------------------------------------
:: Replace the placeholder with the absolute path to your real CSV file
set "REAL_DATA_PATH=C:\Users\Anmol\OneDrive\Desktop\MuleNet\processed_paysim.csv"
set "MLFLOW_TRACKING_URI=file:///tmp/mlruns"

:: ------------------------------------------------------------
:: 4 Change to the training scripts folder
:: ------------------------------------------------------------
pushd ml_service\training

:: ------------------------------------------------------------
:: 5 Run each training script sequentially
:: ------------------------------------------------------------
python train_xgboost.py
python train_gnn.py
python train_isolation_forest.py

:: Return to the repository root
popd

:: ------------------------------------------------------------
:: 6 Package the trained artefacts
:: ------------------------------------------------------------
if not exist "ml_service\trained_models" (
    echo [WARNING] trained_models folder not found – creating empty folder.
    mkdir "ml_service\trained_models"
)

:: Use PowerShell's Compress-Archive to create a zip archive
powershell -Command "Compress-Archive -Path 'ml_service\trained_models\*' -DestinationPath 'ml_service\trained_models.zip' -Force"

:: ------------------------------------------------------------
:: 7 Quick sanity‑check – list what was saved
:: ------------------------------------------------------------
echo === Saved artefacts ===
for %%F in (ml_service\trained_models\*) do echo - %%~nF

:: End of script
