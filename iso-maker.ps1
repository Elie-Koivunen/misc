# Create-Win11VMISO.ps1
# Creates a bootable Windows 11 ISO for VMware from extracted ISO files
# and an existing autounattend.xml. Requires Windows ADK Deployment Tools (oscdimg).
$ErrorActionPreference = 'Stop'

function Read-ExistingPath([string]$Prompt, [string]$Type) {
    while ($true) {
        $entered = (Read-Host $Prompt).Trim().Trim('"')
        if (-not $entered) { Write-Warning 'Enter a path.'; continue }
        try { $path = (Resolve-Path -LiteralPath $entered -ErrorAction Stop).ProviderPath }
        catch { Write-Warning "Path not found: $entered"; continue }
        if ($Type -eq 'Directory' -and (Test-Path -LiteralPath $path -PathType Container)) { return $path }
        if ($Type -eq 'File' -and (Test-Path -LiteralPath $path -PathType Leaf)) { return $path }
        Write-Warning "Expected a $Type at: $path"
    }
}

try {
    $source = Read-ExistingPath 'Path to extracted Windows 11 ISO folder' 'Directory'
    $answer = Read-ExistingPath 'Path to your autounattend.xml file' 'File'

    foreach ($required in @('setup.exe','sources\boot.wim','boot\etfsboot.com','efi\microsoft\boot\efisys.bin')) {
        if (-not (Test-Path -LiteralPath (Join-Path $source $required) -PathType Leaf)) {
            throw "Missing '$required'. Select the ROOT of the extracted Windows 11 ISO."
        }
    }

    # Check XML syntax (Windows Setup itself validates answer-file semantics).
    try { $null = [xml](Get-Content -LiteralPath $answer -Raw -Encoding UTF8) }
    catch { throw "Answer file is not well-formed XML: $($_.Exception.Message)" }

    # Find oscdimg in ADK or on PATH.
    $tool = Get-Command oscdimg.exe -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Source
    if (-not $tool) {
        $kits = Join-Path ${env:ProgramFiles(x86)} 'Windows Kits\10\Assessment and Deployment Kit\Deployment Tools\amd64\Oscdimg\oscdimg.exe'
        if (Test-Path -LiteralPath $kits -PathType Leaf) { $tool = $kits }
    }
    if (-not $tool) {
        throw 'oscdimg.exe not found. Install Windows ADK > Deployment Tools first.'
    }

    $parent = Split-Path -Parent $source
    $output = Join-Path $parent 'win11-vm.iso'
    if (Test-Path -LiteralPath $output) { throw "Output already exists: $output (move or rename it first)." }

    # Stage files so extracted ISO directory remains untouched.
    $stage = Join-Path ([IO.Path]::GetTempPath()) ('Win11ISO-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $stage -Force | Out-Null
    try {
        Write-Host "Copying files to temporary folder: $stage"
        & robocopy.exe $source $stage /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP
        if ($LASTEXITCODE -ge 8) { throw "Robocopy failed (exit code $LASTEXITCODE)." }

        Copy-Item -LiteralPath $answer -Destination (Join-Path $stage 'autounattend.xml') -Force

        $bios = Join-Path $stage 'boot\etfsboot.com'
        $uefi = Join-Path $stage 'efi\microsoft\boot\efisys.bin'
        # Start-Process handles quoting and whitespace in these paths.
        $boot = '-bootdata:2#p0,e,b"' + $bios + '"#pEF,e,b"' + $uefi + '"'
        $arguments = '-m -o -u2 -udfver102 -lWIN11_VM ' + $boot + ' "' + $stage + '" "' + $output + '"'
        Write-Host "Building ISO: $output"
        $process = Start-Process -FilePath $tool -ArgumentList $arguments -Wait -PassThru -NoNewWindow
        if ($process.ExitCode -ne 0) { throw "oscdimg failed (exit code $($process.ExitCode))." }
        if (-not (Test-Path -LiteralPath $output -PathType Leaf)) { throw 'ISO output was not created.' }
        Write-Host "`nSUCCESS: $output" -ForegroundColor Green
        Write-Host 'Attach this ISO to a VMware Workstation virtual CD/DVD drive.'
    }
    finally {
        if (Test-Path -LiteralPath $stage) {
            Write-Host 'Removing temporary working files...'
            Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}
catch {
    Write-Error $_.Exception.Message
    exit 1
}
