#!/bin/sh

gunicorn -c gunicorn.cfg.py main:app