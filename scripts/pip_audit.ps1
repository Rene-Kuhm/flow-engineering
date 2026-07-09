$ErrorActionPreference = "Stop"

$requirementsFile = Join-Path ([System.IO.Path]::GetTempPath()) "flow-engineering-pip-audit-$PID-$([guid]::NewGuid()).txt"
$exitCode = 1

try {
    & uv export --locked --all-extras --format requirements.txt --no-emit-project --no-hashes --output-file $requirementsFile
    if ($LASTEXITCODE -ne 0) {
        $exitCode = $LASTEXITCODE
    }
    else {
        & uv run --locked pip-audit --strict --format=json --requirement $requirementsFile
        $exitCode = $LASTEXITCODE
    }
}
finally {
    Remove-Item -LiteralPath $requirementsFile -Force -ErrorAction SilentlyContinue
}

exit $exitCode
