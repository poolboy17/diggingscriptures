@echo off
cd /d D:\dev\projects\diggingscriptures
set PYTHONIOENCODING=utf-8
python silo_mapper.py --analyze > _silo_analysis.txt 2>&1
echo DONE >> _silo_analysis.txt
