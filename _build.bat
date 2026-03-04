@echo off
cd /d D:\dev\projects\diggingscriptures
set PYTHONIOENCODING=utf-8
call npx astro build > _build_log.txt 2>&1
echo EXIT_CODE=%ERRORLEVEL% >> _build_log.txt
