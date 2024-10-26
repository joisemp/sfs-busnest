#!/bin/bash

# Change to the src directory
cd src

# Set the DJANGO_SETTINGS_MODULE environment variable
export DJANGO_SETTINGS_MODULE=config.test_settings

# Generate a new secret key (you can customize the method to generate the key)
export DJANGO_SECRET_KEY=$(openssl rand -base64 32)

# Optionally, you can echo the secret key for debugging (comment this out in production)
# echo "Using Secret Key: $DJANGO_SECRET_KEY"

# Run the Django tests
python manage.py test
