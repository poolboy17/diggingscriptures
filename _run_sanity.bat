@echo off
cd /d D:\dev\projects\diggingscriptures
set PYTHONIOENCODING=utf-8
python _sanity_check.py > _sanity_results.txt 2>&1
echo === DONE === >> _sanity_results.txt
