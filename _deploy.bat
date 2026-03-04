@echo off
cd /d D:\dev\projects\diggingscriptures
call npx netlify deploy --prod --dir=dist --site=18c0f63d-4335-4206-9a5b-13d5bb6d31b6 > _deploy_log.txt 2>&1
echo EXIT_CODE=%ERRORLEVEL% >> _deploy_log.txt
