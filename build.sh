#!/usr/bin/env bash
# Build script for Render single-URL deployment.
# 1) Install Python deps for FastAPI backend
# 2) Install Node deps and build the React frontend
# Backend will serve the React build at root and the API under /api.
set -e

echo "==> Installing Python dependencies"
pip install --upgrade pip
pip install -r backend/requirements.txt

echo "==> Installing frontend dependencies"
cd frontend
if command -v yarn >/dev/null 2>&1; then
  yarn install --frozen-lockfile || yarn install
else
  npm install --legacy-peer-deps
fi

echo "==> Building React frontend"
if command -v yarn >/dev/null 2>&1; then
  yarn build
else
  npm run build
fi

cd ..
echo "==> Build complete. Frontend build at frontend/build, backend at backend/"
