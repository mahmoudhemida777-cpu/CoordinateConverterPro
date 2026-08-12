; Coordinate Converter Pro — Inno Setup installer script
; Builds CoordinateConverterPro_Setup.exe from the PyInstaller one-folder
; output produced by .github/workflows/build-windows.yml

#define MyAppName "Coordinate Converter Pro"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Coordinate Converter Pro"
#define MyAppExeName "CoordinateConverterPro.exe"

[Setup]
AppId={{B3D3E9F0-6C1A-4E6B-9C3E-COORDCONV0001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=CoordinateConverterPro_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

; Pulls in the entire PyInstaller one-folder output (all Qt DLLs/plugins,
; PROJ data files, everything) — not just the EXE.
[Files]
Source: "..\dist\CoordinateConverterPro\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
