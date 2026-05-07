#!/bin/bash
echo "=== TalentLens Setup ==="
pip install django
python manage.py migrate
echo ""
echo "=== Setup Complete ==="
echo "Run: python manage.py runserver"
echo "Open: http://127.0.0.1:8000/login/"
echo "Login: superadmin@demo.com / demo123"
