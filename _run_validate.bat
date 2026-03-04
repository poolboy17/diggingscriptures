@echo off
cd /d D:\dev\projects\diggingscriptures
set PYTHONIOENCODING=utf-8
python _validate_pyramid.py > _validate_results.txt 2>&1
echo DONE >> _validate_results.txt
