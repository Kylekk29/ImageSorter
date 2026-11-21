; Build this installer with build.ps1 and the Inno Setup command-line compiler.
; BuildVersion is supplied by build.ps1 from main.APP_VERSION.
#define AppName "Turbo Photo Sorter"
#define AppExe "TurboPhotoSorter.exe"
#define ArtifactPrefix "TurboPhotoSorter-" + BuildVersion + "-x64"

[Setup]
AppId=Kylekk29.TurboPhotoSorter
AppName={#AppName}
AppVersion={#BuildVersion}
AppPublisher=Kylekk29
AppPublisherURL=https://github.com/Kylekk29/ImageSorter
AppSupportURL=https://github.com/Kylekk29/ImageSorter/issues
AppUpdatesURL=https://github.com/Kylekk29/ImageSorter/releases
VersionInfoVersion={#BuildVersion}
VersionInfoDescription={#AppName} Setup
VersionInfoProductName={#AppName}
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\{#AppName}
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#AppExe}
LicenseFile=..\LICENSE
SetupIconFile=..\assets\app.ico
OutputDir=..\dist
OutputBaseFilename={#ArtifactPrefix}-Setup
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
RestartApplications=no

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\{#ArtifactPrefix}-Portable.exe"; DestDir: "{app}"; DestName: "{#AppExe}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
