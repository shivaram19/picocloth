#!/bin/bash
cd linkedin-scraper
source ../linkedin-env/bin/activate
python3 scraper_fast.py --profile \"$1\" --attach --headless
