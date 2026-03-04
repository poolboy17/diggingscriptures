@echo off
cd /d D:\dev\projects\diggingscriptures
set PYTHONIOENCODING=utf-8
python internal_linker.py --fix > _linker_results.txt 2>&1
echo DONE >> _linker_results.txt
