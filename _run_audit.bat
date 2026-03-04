@echo off
cd /d D:\dev\projects\diggingscriptures
set PYTHONIOENCODING=utf-8
python semantic-pipe-research.py --audit-only > _audit_results.txt 2>&1
echo === DONE === >> _audit_results.txt
