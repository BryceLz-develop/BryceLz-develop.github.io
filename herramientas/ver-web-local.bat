@echo off
rem Abre la copia local de la web (docs-local/, con las apps en desarrollo) en http://localhost:8080
cd /d "%~dp0.."
start "" http://localhost:8080/
node herramientas\servidor-local.js
