@echo off
setlocal
title ApexDrive - Local RAG Assistant
cd /d "%~dp0"

set "APEX_PYTHON=%~dp0.venv\Scripts\python.exe"
set "PYTHONDONTWRITEBYTECODE=1"
if not defined HOST set "HOST=127.0.0.1"
if not defined PORT set "PORT=8000"
if not defined OLLAMA_BASE_URL set "OLLAMA_BASE_URL=http://127.0.0.1:11434"
if not defined OLLAMA_MODEL set "OLLAMA_MODEL=qwen2.5:3b"
if not defined RAG_MODEL set "RAG_MODEL=models\all-MiniLM-L6-v2"
if not defined RAG_INDEX set "RAG_INDEX=data\index.sqlite3"

echo ============================================================
echo   ApexDrive - Local RAG Assistant
echo ============================================================
echo.

if not exist "%APEX_PYTHON%" goto missing_python
"%APEX_PYTHON%" -c "import fastapi, uvicorn, httpx, numpy, sentence_transformers" >nul 2>&1
if errorlevel 1 goto missing_dependencies
if not exist "%RAG_MODEL%\modules.json" goto missing_embedding

if exist "%RAG_INDEX%" goto check_ollama
echo Building the local document index. This may take a moment...
"%APEX_PYTHON%" -m scripts.index_documents
if errorlevel 1 goto failed

:check_ollama
echo Checking Ollama...
"%APEX_PYTHON%" -c "import os,httpx; httpx.get(os.environ['OLLAMA_BASE_URL']+'/api/tags',timeout=3).raise_for_status()" >nul 2>&1
if not errorlevel 1 goto check_llm

rem Only automatically start the default local Ollama service.
if /i not "%OLLAMA_BASE_URL%"=="http://127.0.0.1:11434" goto ollama_unavailable
echo Starting Ollama in the background...
powershell -NoProfile -Command "$exe = (Get-Command ollama.exe -ErrorAction SilentlyContinue).Source; if (-not $exe) { $exe = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe' }; if (-not (Test-Path -LiteralPath $exe)) { exit 1 }; Start-Process -FilePath $exe -ArgumentList 'serve' -WindowStyle Hidden; for ($attempt = 0; $attempt -lt 20; $attempt++) { try { $null = Invoke-RestMethod -Uri ($env:OLLAMA_BASE_URL + '/api/tags') -TimeoutSec 1; exit 0 } catch { Start-Sleep -Seconds 1 } }; exit 1"
if errorlevel 1 goto ollama_unavailable

:check_llm
"%APEX_PYTHON%" -c "import os,sys,httpx; names=[m['name'] for m in httpx.get(os.environ['OLLAMA_BASE_URL']+'/api/tags',timeout=5).json().get('models',[])]; model=os.environ['OLLAMA_MODEL']; sys.exit(0 if model in names or model+':latest' in names else 1)" >nul 2>&1
if errorlevel 1 goto missing_llm

echo.
echo Open http://localhost:%PORT% in your browser once startup completes.
echo Keep this window open. Press Ctrl+C to stop the assistant.
echo Ollama will remain running for future sessions.
echo.
"%APEX_PYTHON%" -m scripts.run_server
if errorlevel 1 goto failed
goto end

:missing_python
echo [ERROR] Project Python environment is missing.
echo Follow the setup instructions in README.md to create .venv.
goto failed

:missing_dependencies
echo [ERROR] Required Python packages could not be loaded.
echo Install them in the project environment:
echo   "%APEX_PYTHON%" -m pip install -r requirements.txt
goto failed

:missing_embedding
echo [ERROR] Local embedding model is missing from "%RAG_MODEL%".
echo Provision it once with an internet connection:
echo   "%APEX_PYTHON%" -m scripts.download_embedding_model
goto failed

:missing_llm
echo [ERROR] The configured generation model is not available in Ollama.
echo Download it once with:
echo   ollama pull %OLLAMA_MODEL%
goto failed

:ollama_unavailable
echo [ERROR] Cannot reach Ollama at %OLLAMA_BASE_URL%.
echo Install Ollama if needed, run "ollama serve", and try again.
goto failed

:failed
echo.
echo Startup stopped. See the message above and README.md for help.
pause
endlocal
exit /b 1

:end
endlocal
exit /b 0
