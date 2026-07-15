#define AppName "Local Transcriber Pro"
#ifndef AppVersion
  #define AppVersion "2.1.0"
#endif
#define AppPublisher "Vhaloo"
#define AppExeName "LocalTranscriberPro.exe"

[Setup]
AppId={{B73984E1-D932-4C45-A042-CE70D7C29D4A}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL=https://github.com/vhaloo/LocalTranscriberPro
AppSupportURL=https://github.com/vhaloo/LocalTranscriberPro/issues
DefaultDirName={localappdata}\Programs\Local Transcriber Pro
DefaultGroupName=Local Transcriber Pro
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\..\artifacts
OutputBaseFilename=LocalTranscriberPro-{#AppVersion}-Windows-x64-Setup
SetupIconFile=..\..\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
DisableProgramGroupPage=yes
LicenseFile=..\..\LICENSE
ChangesEnvironment=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\..\dist\LocalTranscriberPro\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Local Transcriber Pro"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\Local Transcriber Pro"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,Local Transcriber Pro}"; Flags: nowait postinstall skipifsilent
