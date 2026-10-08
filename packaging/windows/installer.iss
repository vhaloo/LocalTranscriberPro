#define AppName "Local Transcriber Pro"
#ifndef AppVersion
  #define AppVersion "3.1.0"
#endif
#ifndef AppSource
  #define AppSource "..\..\dist\" + AppVersion + "\LocalTranscriberPro"
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
LZMAUseSeparateProcess=yes
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
english.PreflightSummary=Detected RAM: %1 GB%nFree storage: %2 GB%n%nIncluded automatically:%n• Qwen3-ASR, Parakeet and Whisper local engines%n• NVIDIA CUDA compatibility runtime and safe CPU fallback%n• FFmpeg audio/video helper%n• Microphone and speaker-identification libraries%n• French and English interfaces%n• Verified updates from the official repository%n%nSpeech models are downloaded when selected, including Automatic (0.08 to 6.2 GB including alignment). The application will disable models exceeding its conservative resource limits.
english.RamTooLow=This computer has only %1 GB of RAM. Local Transcriber Pro requires at least 3.5 GB so that Tiny cannot exhaust the system. Installation was stopped safely.
french.PreflightTitle=Prêt pour cet ordinateur
french.PreflightDescription=L’installateur a vérifié l’essentiel avant de copier quoi que ce soit.
french.PreflightSubCaption=Local Transcriber Pro est autonome. Il n’est pas nécessaire d’installer Python, CUDA ou FFmpeg.
french.PreflightSummary=RAM détectée : %1 Go%nStockage libre : %2 Go%n%nInclus automatiquement :%n• Moteurs locaux Qwen3-ASR, Parakeet et Whisper%n• Compatibilité NVIDIA CUDA et repli CPU sûr%n• Outil audio/vidéo FFmpeg%n• Microphone et identification des personnes%n• Interfaces française et anglaise%n• Mises à jour vérifiées depuis le dépôt officiel%n%nLes modèles sont téléchargés lors de leur sélection, y compris Automatique (0,08 à 6,2 Go avec alignement). Les modèles dépassant les limites de ressources sont désactivés.
french.RamTooLow=Cet ordinateur possède seulement %1 Go de RAM. Local Transcriber Pro exige au moins 3,5 Go afin que même Tiny ne puisse pas épuiser le système. L’installation a été arrêtée sans risque.

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[InstallDelete]
; Remove obsolete dependency DLLs/metadata before copying the new bundle.
; User settings, history, models and recordings live outside this directory.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
#ifdef SyntaxOnly
Source: "..\..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
#else
Source: "{#AppSource}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
#endif

[Icons]
Name: "{group}\Local Transcriber Pro"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\Local Transcriber Pro"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,Local Transcriber Pro}"; Flags: nowait postinstall skipifsilent
Filename: "{app}\{#AppExeName}"; Flags: nowait runasoriginaluser; Check: IsAutomaticUpdate

[Code]
function OpenProcess(Access: LongWord; Inherit: Integer; ProcessId: LongWord): THandle;
  external 'OpenProcess@kernel32.dll stdcall';
function WaitForSingleObject(Handle: THandle; Milliseconds: LongWord): LongWord;
  external 'WaitForSingleObject@kernel32.dll stdcall';
function CloseHandle(Handle: THandle): Integer;
  external 'CloseHandle@kernel32.dll stdcall';

var
  PreflightPage: TOutputMsgMemoWizardPage;
  DetectedRamGB: Extended;
  FreeDiskGB: Extended;

function IsAutomaticUpdate(): Boolean;
begin
  Result := Pos('/AUTOUPDATE', UpperCase(GetCmdTail)) > 0;
end;

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
var
  PreviousProcessId: Integer;
  PreviousProcess: THandle;
  WaitResult: LongWord;
begin
  Result := True;
  PreviousProcessId := StrToIntDef(ExpandConstant('{param:WAITPID|0}'), 0);
  if IsAutomaticUpdate() and (PreviousProcessId > 0) then
  begin
    { InitializeSetup runs before Inno's AppMutex and file-in-use checks. Wait
      for the actual process exit, not a guessed delay or an early mutex release. }
    PreviousProcess := OpenProcess($00100000, 0, PreviousProcessId);
    if PreviousProcess <> 0 then
    begin
      Log(Format('Waiting for previous application process %d to exit.', [PreviousProcessId]));
      try
        WaitResult := WaitForSingleObject(PreviousProcess, 600000);
      finally
        CloseHandle(PreviousProcess);
      end;
      if WaitResult <> 0 then
      begin
        Log('Previous application did not exit; update stopped without replacing files.');
        Result := False;
        Exit;
      end;
      Log('Previous application exited; safe to replace the runtime.');
    end
    else
      Log('Previous application process has already exited.');
  end;
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
