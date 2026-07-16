#define AppName "Local Transcriber Pro"
#ifndef AppVersion
  #define AppVersion "2.2.0"
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
MinVersion=10.0.17763
OutputDir=..\..\artifacts
#ifdef SyntaxOnly
OutputBaseFilename=LocalTranscriberPro-Installer-SyntaxTest
#else
OutputBaseFilename=LocalTranscriberPro-{#AppVersion}-Windows-x64-Setup
#endif
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
SetupLogging=yes
AppMutex=LocalTranscriberPro-Desktop-v2

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[CustomMessages]
english.PreflightTitle=Ready for this computer
english.PreflightDescription=The installer checked the essentials before copying anything.
english.PreflightSubCaption=Local Transcriber Pro is self-contained. No Python, CUDA toolkit or FFmpeg installation is required.
english.PreflightSummary=Detected RAM: %1 GB%nFree storage: %2 GB%n%nIncluded automatically:%n• Private CPU transcription engine%n• NVIDIA CUDA compatibility runtime and safe CPU fallback%n• FFmpeg audio/video helper%n• Microphone and speaker-identification libraries%n• French and English interfaces%n%nSpeech models are downloaded only when selected (0.08 to 3.10 GB). The application will disable any model this computer cannot run safely.
english.RamTooLow=This computer has only %1 GB of RAM. Local Transcriber Pro requires at least 3.5 GB so that Tiny cannot exhaust the system. Installation was stopped safely.
french.PreflightTitle=Prêt pour cet ordinateur
french.PreflightDescription=L’installateur a vérifié l’essentiel avant de copier quoi que ce soit.
french.PreflightSubCaption=Local Transcriber Pro est autonome. Il n’est pas nécessaire d’installer Python, CUDA ou FFmpeg.
french.PreflightSummary=RAM détectée : %1 Go%nStockage libre : %2 Go%n%nInclus automatiquement :%n• Moteur privé de transcription CPU%n• Moteur de compatibilité NVIDIA CUDA et repli CPU sûr%n• Outil audio/vidéo FFmpeg%n• Bibliothèques pour le microphone et l’identification des personnes%n• Interfaces française et anglaise%n%nLes modèles vocaux sont téléchargés seulement lorsqu’ils sont choisis (0,08 à 3,10 Go). L’application désactivera tout modèle que cet ordinateur ne peut pas lancer sans risque.
french.RamTooLow=Cet ordinateur possède seulement %1 Go de RAM. Local Transcriber Pro exige au moins 3,5 Go afin que même Tiny ne puisse pas épuiser le système. L’installation a été arrêtée sans risque.

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
#ifdef SyntaxOnly
Source: "..\..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
#else
Source: "..\..\dist\LocalTranscriberPro\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
#endif

[Icons]
Name: "{group}\Local Transcriber Pro"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\Local Transcriber Pro"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,Local Transcriber Pro}"; Flags: nowait postinstall skipifsilent

[Code]
var
  PreflightPage: TOutputMsgMemoWizardPage;
  DetectedRamGB: Extended;
  FreeDiskGB: Extended;

function DetectRamGB(): Extended;
var
  Locator, Services, Items, Item: Variant;
  Bytes: Int64;
begin
  Result := 0;
  try
    Locator := CreateOleObject('WbemScripting.SWbemLocator');
    Services := Locator.ConnectServer('.', 'root\CIMV2');
    Items := Services.ExecQuery('SELECT TotalPhysicalMemory FROM Win32_ComputerSystem');
    Item := Items.ItemIndex(0);
    Bytes := Item.TotalPhysicalMemory;
    Result := Bytes / 1073741824;
  except
    Result := 0;
  end;
end;

function DetectFreeDiskGB(): Extended;
var
  FreeBytes, TotalBytes: Int64;
begin
  Result := 0;
  if GetSpaceOnDisk64(ExpandConstant('{localappdata}'), FreeBytes, TotalBytes) then
    Result := FreeBytes / 1073741824;
end;

function InitializeSetup(): Boolean;
begin
  DetectedRamGB := DetectRamGB();
  FreeDiskGB := DetectFreeDiskGB();
  Result := True;
  if (DetectedRamGB > 0) and (DetectedRamGB < 3.5) then
  begin
    MsgBox(FmtMessage(ExpandConstant('{cm:RamTooLow}'), [Format('%.1f', [DetectedRamGB])]), mbError, MB_OK);
    Result := False;
  end;
end;

procedure InitializeWizard();
var
  Summary: String;
begin
  Summary := FmtMessage(ExpandConstant('{cm:PreflightSummary}'), [Format('%.1f', [DetectedRamGB]), Format('%.1f', [FreeDiskGB])]);
  PreflightPage := CreateOutputMsgMemoPage(
    wpSelectDir,
    ExpandConstant('{cm:PreflightTitle}'),
    ExpandConstant('{cm:PreflightDescription}'),
    ExpandConstant('{cm:PreflightSubCaption}'),
    Summary
  );
end;
