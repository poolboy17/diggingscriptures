@echo off
cd /d D:\dev\projects\diggingscriptures
set PYTHONIOENCODING=utf-8
python _run_relink.py > _relink_results.txt 2>&1
echo DONE >> _relink_results.txt
