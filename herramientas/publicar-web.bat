@echo off
rem Publica la web de BryceLz: proyecto a "fuente" y docs a "main" (GitHub Pages).
rem Antes: python build.py y commit de los cambios.
setlocal
cd /d "%~dp0.."
set "LOG=%~dp0publicar.log"
echo inicio %date% %time% > "%LOG%"
git push origin HEAD:fuente >> "%LOG%" 2>&1
echo PUSH FUENTE %ERRORLEVEL% >> "%LOG%"
git branch -D sitio >nul 2>&1
git subtree split --prefix docs -b sitio >> "%LOG%" 2>&1
git push origin sitio:main >> "%LOG%" 2>&1
echo PUSH MAIN %ERRORLEVEL% >> "%LOG%"
echo FIN >> "%LOG%"
