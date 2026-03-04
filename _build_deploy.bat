@echo off
cd /d D:\dev\projects\diggingscriptures
set PYTHONIOENCODING=utf-8
echo === ASTRO BUILD === >> _build_deploy_log.txt
call npx astro build >> _build_deploy_log.txt 2>&1
echo BUILD_EXIT=%ERRORLEVEL% >> _build_deploy_log.txt
echo === NETLIFY DEPLOY === >> _build_deploy_log.txt
call npx netlify deploy --prod --dir=dist --site=18c0f63d-4335-4206-9a5b-13d5bb6d31b6 >> _build_deploy_log.txt 2>&1
echo DEPLOY_EXIT=%ERRORLEVEL% >> _build_deploy_log.txt
echo DONE >> _build_deploy_log.txt
