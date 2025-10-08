#!/bin/bash
# Setup PostgreSQL database for feature-frontend
# Run this with: bash setup_database.sh

echo "Creating PostgreSQL database and user..."

# Connect to PostgreSQL as postgres user and create database
psql -h localhost -p 5432 -U postgres -d postgres <<EOF
-- Drop existing database and user if they exist
DROP DATABASE IF EXISTS feature_frontend;
DROP USER IF EXISTS feature_user;

-- Create user
CREATE USER feature_user WITH ENCRYPTED PASSWORD '3818919Held!';

-- Create database
CREATE DATABASE feature_frontend OWNER feature_user;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE feature_frontend TO feature_user;

\q
EOF

echo "Database setup complete!"
echo "Now run: source .venv/bin/activate && python -m alembic upgrade head"
