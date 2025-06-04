#!/bin/bash
cd /var/www/html/rhscrap
source venv/bin/activate
cd api
sudo python3 app.py
