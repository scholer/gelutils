@echo off
REM %0 is filepath of this batch file. %~dp0 is drive and path of batch file.
REM Alternatively, make a .lnk, but that requires an absolute path.
REM Activate alternative environment (use 'call' when you are in a batch script).
REM - Alternatively, call the environment-specific python.
REM call activate oldpil
REM "C:\Program Files (x86)\Anaconda\envs\oldpil\python.exe" %~dp0\..\gelutils\gelannotator_gui.py %1

REM activate py3pip
REM python %~dp0\..\gelutils\gelannotator_gui.py %1 --filename_substitution "-[SYBR Gold]" "" --openwebbrowser
C:\Users\scholer\Anaconda3\envs\py3pip\python.exe C:\Users\scholer\Dev\src-repos\gelutils\gelutils\gelannotator_gui.py %1 --filename_substitution "-[SYBR Gold]" "" --openwebbrowser --loglevel DEBUG --disable-logging

REM python -c "print('hej')"

IF ERRORLEVEL 1 pause
REM pause