#!/bin/sh
./setup.sh

cd ..

# Loop indefinitely
while true; do
  # Execute your script
  PYTHONUNBUFFERED=1 python dosvob.py
  sleep 4h
done
