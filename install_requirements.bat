@echo off
title Installing Project Requirements
echo Installing necessary Python libraries (Django, TensorFlow, etc.)...
echo This might take a few minutes. Please wait...

pip install -r requirements.txt

echo.
echo ========================================================
echo Installation Complete! You can now run the server.
echo ========================================================
pause
