#!/bin/bash

# Gunicorn run script for deploying Flask app on Vercel

# Ensure the database exists before starting Gunicorn
if [ ! -f "Ritualsproduct.db" ]; then
    echo "Database file Ritualsproduct.db not found!"
    exit 1
fi

# Start the Flask application using Gunicorn
gunicorn app:app --workers 3 --bind 0.0.0.0:$PORT
