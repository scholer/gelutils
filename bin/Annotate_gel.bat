@echo off
REM %0 is filepath of this batch file. %~dp0 is drive and path of batch file.
REM Activate python environment if needed, use 'call' when you are in a batch script.
REM Alternatively, call the environment-specific python interpreter using its full path.

REM Using annotate_gel.py script:
echo OBS: Using batch scripts is obsolete! Use pip/conda to install and then use the created AnnotateGel executables in your Python's bin/ directory.
call activate py3pip
python.exe %~dp0\annotate_gel.py %*

IF ERRORLEVEL 1 pause
