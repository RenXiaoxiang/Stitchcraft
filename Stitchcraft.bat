@echo off
rem Stitchcraft Studio launcher (Windows).
rem Double-click this file to start the local studio and open it in an Edge app window.
chcp 65001 >nul
title Stitchcraft Studio
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Python 3.11+ was not found on PATH.
  echo Install Python from https://www.python.org/downloads/ and try again.
  pause
  exit /b 1
)

python -m stitchcraft app %*
if errorlevel 1 (
  echo.
  echo Stitchcraft Studio exited with an error.
  pause
)
