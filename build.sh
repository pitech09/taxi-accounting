<<<<<<< HEAD
#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install dependencies
pip install --upgrade pip
=======
#!/bin/bash
# build.sh

# Install dependencies
>>>>>>> 64e423b7ca903465804b98ca16d473e9acfe4f87
pip install -r requirements.txt

# Run migrations
python manage.py migrate --noinput

# Collect static files
<<<<<<< HEAD
python manage.py collectstatic --noinput

# Create superuser if not exists (optional - uncomment for production)
# python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@example.com', 'admin123') if not User.objects.filter(username='admin').exists() else None"
=======
python manage.py collectstatic --noinput
>>>>>>> 64e423b7ca903465804b98ca16d473e9acfe4f87
