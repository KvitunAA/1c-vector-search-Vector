@echo off
REM MCP-сервер your_project: переносимый скрипт (пути относительно расположения)

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"
if exist "%SCRIPT_DIR%local.env" for /f "usebackq eol=# tokens=1,* delims==" %%a in ("%SCRIPT_DIR%local.env") do if "%%a"=="VECTOR_PYTHON_PATH" set "VECTOR_PYTHON_PATH=%%b"

set PROJECT_PROFILE=your_project
set VECTORDB_PATH=%SCRIPT_DIR%projects\your_project\vectordb
set GRAPHDB_PATH=%SCRIPT_DIR%projects\your_project\graphdb\graph.db

set "PYTHON=python"
if defined VECTOR_PYTHON_PATH set "PYTHON=%VECTOR_PYTHON_PATH%"

"%PYTHON%" "%SCRIPT_DIR%run_server.py"
