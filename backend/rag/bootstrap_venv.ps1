# Tạo lại .venv sạch (Python 3.13 — máy bạn chỉ có bản này) và cài requirements.
# Chạy từ thư mục backend\rag:  .\bootstrap_venv.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$py = (Get-Command py -ErrorAction SilentlyContinue)
if ($py) {
    py -3.13 -m venv .venv
} else {
    & "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe" -m venv .venv
}

& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
& ".\.venv\Scripts\python.exe" -c "import sklearn; print('scikit-learn', sklearn.__version__)"
