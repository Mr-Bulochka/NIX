@echo off
rem NIX launcher. Resolves the repo root and prefers the local venv so the
rem installed console script never shadows this checkout.
setlocal

pushd "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m nix %*
) else (
    echo [nix] .venv not found, falling back to python on PATH.
    python -m nix %*
)

popd
endlocal
