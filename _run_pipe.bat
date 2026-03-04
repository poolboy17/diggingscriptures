@echo off
cd /d D:\dev\projects\diggingscriptures
set PYTHONIOENCODING=utf-8
echo === PIPELINE v2.1 REGEN-FAQ PASS 2 === > _pipe_log.txt
echo %date% %time% >> _pipe_log.txt
python semantic-pipe-research.py --all --force --regen-faq >> _pipe_log.txt 2>&1
echo === DONE === >> _pipe_log.txt
echo %date% %time% >> _pipe_log.txt