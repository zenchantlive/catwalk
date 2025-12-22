#!/bin/bash
# Script to verify AUTH_SECRET matches between frontend and backend

echo "=== JWT Secret Verification ==="
echo ""

# Get frontend AUTH_SECRET
cd "$(dirname "$0")/frontend"
if [ -f .env.local ]; then
    FRONTEND_SECRET=$(grep '^AUTH_SECRET=' .env.local | cut -d '=' -f2- | tr -d '"' | tr -d "'")
    echo "Frontend AUTH_SECRET (from .env.local):"
    echo "  First 20 chars: ${FRONTEND_SECRET:0:20}..."
    echo "  Length: ${#FRONTEND_SECRET}"
else
    echo "ERROR: frontend/.env.local not found!"
    exit 1
fi

echo ""
echo "Backend AUTH_SECRET (from Fly.io):"
echo "  Run this command to check:"
echo "  fly ssh console --app catwalk-live-backend-dev -C 'echo \$AUTH_SECRET | cut -c1-20'"
echo ""
echo "If they don't match, set the backend secret with:"
echo "  fly secrets set AUTH_SECRET=\"$FRONTEND_SECRET\" --app catwalk-live-backend-dev"
