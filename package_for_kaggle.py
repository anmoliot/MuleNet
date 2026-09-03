import os
import zipfile
import pathlib

def create_kaggle_zip():
    # The directory where this script is running (MuleNet root)
    base_dir = pathlib.Path(__file__).parent.resolve()
    zip_filename = base_dir / "mulenet_for_kaggle.zip"
    
    # Folders and files to completely ignore (saves space and upload time)
    exclude_dirs = {'.git', '.pytest_cache', 'venv', '__pycache__', 'node_modules', '.idea', '.vscode'}
    exclude_exts = {'.pyc', '.zip', '.log'}

    print(f"Packaging local repository into: {zip_filename.name}")
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(base_dir):
            # Modify dirs in-place to skip excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                # Skip excluded file extensions
                if any(file.endswith(ext) for ext in exclude_exts):
                    continue
                    
                file_path = pathlib.Path(root) / file
                
                # Skip the zip file itself if it's in the directory
                if file_path == zip_filename:
                    continue
                    
                # Calculate the relative path to maintain folder structure inside the zip
                arcname = file_path.relative_to(base_dir)
                
                # We mainly need the ml_service folder and root files for training.
                # You can comment out the if statement below if you want to zip the ENTIRE repo (frontend/backend).
                if str(arcname).startswith('ml_service') or len(arcname.parts) == 1:
                    zipf.write(file_path, arcname)
                
    print(f"Successfully created {zip_filename.name}!")
    print(f"You can now upload this file to Kaggle as a dataset.")

if __name__ == "__main__":
    create_kaggle_zip()
