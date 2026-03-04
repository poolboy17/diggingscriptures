@echo off
cd /d D:\dev\projects\diggingscriptures
set PYTHONIOENCODING=utf-8
python semantic-pipe-research.py --all --force --aeo-harden > _aeo_results2.txt 2>&1
echo === DONE === >> _aeo_results2.txt
