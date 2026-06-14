$src = Join-Path $PSScriptRoot '..\.env.example'
$dst = Join-Path $PSScriptRoot '..\.env'
if (-Not (Test-Path $dst)) {
    Copy-Item $src $dst -Force
    Write-Output "Created .env from .env.example at $dst. Edit it and set real keys."
} else {
    Write-Output ".env already exists at $dst"
}
