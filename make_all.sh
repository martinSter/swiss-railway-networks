#!/usr/bin/env bash
set -e  # Exit immediately if a command fails
set -x  # Print commands as they run for debugging

# -----------------------------------------
# 1. Create and activate virtual environment
# -----------------------------------------
VENV_DIR=".venv"

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment..."
  python3 -m venv "$VENV_DIR"
fi

echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# -----------------------------------------
# 2. Install dependencies
# -----------------------------------------
if [ -f "requirements.txt" ]; then
  echo "Installing dependencies from requirements.txt..."
  pip install --upgrade pip
  pip install -r requirements.txt
else
  echo "No requirements.txt found — skipping dependency installation."
fi

# -----------------------------------------
# 3. Ensure clean directory exists
# -----------------------------------------
CLEAN_DIR="clean"
if [ ! -d "$CLEAN_DIR" ]; then
  echo "Creating clean directory..."
  mkdir -p "$CLEAN_DIR"
fi

# -----------------------------------------
# 4. Run data processing scripts
# -----------------------------------------
echo "Running data processing scripts..."
python space_of_changes.py
python space_of_stops.py
python space_of_stations.py
python temporal.py

# -----------------------------------------
# 4. Generate checksums for cleaned CSVs
# -----------------------------------------
echo "Generating checksums..."
sha256sum "$CLEAN_DIR"/*.csv > checksums.txt

echo "Checksums written to checksums.txt"

# -----------------------------------------
# 5. Done
# -----------------------------------------
echo "All tasks completed successfully."
