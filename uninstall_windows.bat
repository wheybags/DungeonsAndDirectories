@echo off
@pushd %USERPROFILE%
echo Deleting generated files...
rd /s /q .game
echo Done! You can now just delete this folder
pause
