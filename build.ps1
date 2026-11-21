#requires -Version 5.1
param(
    [string]$Python = "python",
    [string]$InnoCompiler
)

$ErrorActionPreference = "Stop"
Push-Location -LiteralPath $PSScriptRoot
try {
    if ($InnoCompiler) {
        $InnoCompiler = (Get-Command $InnoCompiler -CommandType Application -ErrorAction Stop).Source
    }

    $platform = & $Python -c "import sysconfig; print(sysconfig.get_platform())"
    if ($LASTEXITCODE -ne 0 -or $platform -ne "win-amd64") {
        throw "Build with 64-bit x86 Python on Windows."
    }

    $version = & $Python -c "from main import APP_VERSION; print(APP_VERSION)"
    if ($LASTEXITCODE -ne 0) { throw "Could not read the application version." }

    $pythonBase = & $Python -c "import sys; print(sys.base_prefix)"
    if ($LASTEXITCODE -ne 0) { throw "Could not locate the Python runtime." }

    $name = "TurboPhotoSorter-$version-x64-Portable"
    $buildDir = Join-Path $PSScriptRoot "build"
    $distDir = Join-Path $PSScriptRoot "dist"
    $projectLicense = Join-Path $PSScriptRoot "LICENSE"
    $appIcon = Join-Path $PSScriptRoot "assets/app.ico"
    $arguments = @(
        "-m", "PyInstaller", "--noconfirm", "--onefile", "--windowed", "--name", $name,
        "--specpath", $buildDir, "--workpath", $buildDir, "--distpath", $distDir,
        "--icon", $appIcon, "--add-data", "${appIcon}:assets",
        "--add-data", "${projectLicense}:.",
        "--copy-metadata", "Pillow", "--copy-metadata", "exifread",
        "--copy-metadata", "tkinterdnd2", "--copy-metadata", "pyinstaller"
    )

    $pythonNotice = Join-Path $pythonBase "LICENSE.txt"
    if (Test-Path -LiteralPath $pythonNotice -PathType Leaf) {
        $arguments += @("--add-data", "${pythonNotice}:licenses/python")
    }
    $tkNotice = Join-Path $pythonBase "tcl/tk8.6/license.terms"
    if (Test-Path -LiteralPath $tkNotice -PathType Leaf) {
        $arguments += @("--add-data", "${tkNotice}:licenses/tk")
    }

    & $Python @arguments "main.py"
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE." }
    Get-Item -LiteralPath (Join-Path $distDir "$name.exe")

    if ($InnoCompiler) {
        & $InnoCompiler "/DBuildVersion=$version" (Join-Path $PSScriptRoot "packaging/installer.iss")
        if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed with exit code $LASTEXITCODE." }
        Get-Item -LiteralPath (Join-Path $distDir "TurboPhotoSorter-$version-x64-Setup.exe")
    }
} finally {
    Pop-Location
}
