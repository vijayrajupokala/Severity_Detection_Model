@echo off
title Medical Bug Severity - Starting Server
echo Starting the web server...

:: Attempt to activate Anaconda base environment automatically to load libraries
IF EXIST "%USERPROFILE%\Anaconda3\Scripts\activate.bat" call "%USERPROFILE%\Anaconda3\Scripts\activate.bat"
IF EXIST "%USERPROFILE%\miniconda3\Scripts\activate.bat" call "%USERPROFILE%\miniconda3\Scripts\activate.bat"
IF EXIST "C:\ProgramData\Anaconda3\Scripts\activate.bat" call "C:\ProgramData\Anaconda3\Scripts\activate.bat"
IF EXIST "C:\ProgramData\miniconda3\Scripts\activate.bat" call "C:\ProgramData\miniconda3\Scripts\activate.bat"

:: Open the browser immediately, before runserver blocks
start http://127.0.0.1:8000

:: Run the server bound to 127.0.0.1 to avoid Windows Firewall "office permissions" prompt
python manage.py runserver 127.0.0.1:8000

pause
