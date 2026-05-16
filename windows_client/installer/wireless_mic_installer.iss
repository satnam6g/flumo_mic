; ============================================================================
; wireless_mic_installer.iss  –  Inno Setup 6 script
; Builds:  WirelessMic_Setup.exe
; Requires: Inno Setup 6.x  (https://jrsoftware.org/isinfo.php)
; ============================================================================

#define AppName      "Wireless Mic Client"
#define AppVersion   "1.0.0"
#define AppPublisher "WirelessMic"
#define AppExeName   "WirelessMic.exe"
#define AppId        "{{A7B3C2D1-E4F5-6789-ABCD-EF1234567890}"

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisherURL=https://github.com/wirelessmic
AppSupportURL=https://github.com/wirelessmic/issues
AppUpdatesURL=https://github.com/wirelessmic
DefaultDirName={autopf}\WirelessMic
DefaultGroupName={#AppName}
AllowNoIcons=yes
LicenseFile=..\LICENSE.txt
OutputDir=..\dist_installer
OutputBaseFilename=WirelessMic_Setup
SetupIconFile=..\assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardResizable=yes
DisableProgramGroupPage=no
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}
VersionInfoVersion={#AppVersion}
VersionInfoDescription={#AppName} Installer
VersionInfoCompany={#AppPublisher}

; ── Pages ──────────────────────────────────────────────────────────────────────
[Types]
Name: "full";    Description: "Full installation (recommended)"
Name: "compact"; Description: "Compact (App only)"
Name: "custom";  Description: "Custom"; Flags: iscustom

[Components]
Name: "main";     Description: "Wireless Mic Client (required)"; Types: full compact custom; Flags: fixed
Name: "vbcable";  Description: "VB-Audio Virtual Cable driver";  Types: full
Name: "startup";  Description: "Start with Windows";             Types: full

; ── Files ─────────────────────────────────────────────────────────────────────
[Files]
; Main application (PyInstaller output)
Source: "..\dist\WirelessMic\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: main

; VB-Cable installer (must include the entire folder for INF and SYS files)
Source: "..\vb_cable\*"; DestDir: "{tmp}\vb_cable"; Flags: ignoreversion recursesubdirs createallsubdirs deleteafterinstall skipifsourcedoesntexist; Components: vbcable

; Firewall setup script
Source: "firewall_setup.ps1"; DestDir: "{app}"; Flags: ignoreversion; Components: main

; ── Icons ─────────────────────────────────────────────────────────────────────
[Icons]
Name: "{group}\{#AppName}";           Filename: "{app}\{#AppExeName}";  WorkingDir: "{app}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}";   Filename: "{app}\{#AppExeName}";  WorkingDir: "{app}"; Tasks: desktopicon
Name: "{userstartup}\{#AppName}";     Filename: "{app}\{#AppExeName}";  WorkingDir: "{app}"; Tasks: startuprun; Components: startup

; ── Tasks ─────────────────────────────────────────────────────────────────────
[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut";        GroupDescription: "Additional shortcuts:"
Name: "startuprun";  Description: "Launch &automatically at startup";  GroupDescription: "Startup:"

; ── Run ───────────────────────────────────────────────────────────────────────
[Run]
; Install VB-Cable silently (x64)
Filename: "{tmp}\vb_cable\VBCABLE_Setup_x64.exe"; Parameters: "-i -h"; \
  StatusMsg: "Installing VB-Audio Virtual Cable…"; \
  Flags: waituntilterminated runascurrentuser; \
  Components: vbcable; Check: IsWin64

; Install VB-Cable silently (x86 fallback)
Filename: "{tmp}\vb_cable\VBCABLE_Setup.exe"; Parameters: "-i -h"; \
  StatusMsg: "Installing VB-Audio Virtual Cable (32-bit)…"; \
  Flags: waituntilterminated runascurrentuser; \
  Components: vbcable; Check: not IsWin64

; Add Windows Firewall rule (runs elevated)
Filename: "powershell.exe"; \
  Parameters: "-ExecutionPolicy Bypass -File ""{app}\firewall_setup.ps1"" -Action Add"; \
  StatusMsg: "Configuring Windows Firewall…"; \
  Flags: waituntilterminated runascurrentuser; \
  Components: main

; Offer to launch after install
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName} now"; \
  Flags: nowait postinstall skipifsilent; Components: main

; ── Uninstall Run ─────────────────────────────────────────────────────────────
[UninstallRun]
; Remove firewall rule on uninstall
Filename: "powershell.exe"; \
  Parameters: "-ExecutionPolicy Bypass -File ""{app}\firewall_setup.ps1"" -Action Remove"; \
  Flags: waituntilterminated runascurrentuser

; ── Registry ──────────────────────────────────────────────────────────────────
[Registry]
; Register as installed application
Root: HKLM; Subkey: "Software\{#AppPublisher}\{#AppName}"; \
  ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; \
  Flags: uninsdeletekey; Components: main

Root: HKLM; Subkey: "Software\{#AppPublisher}\{#AppName}"; \
  ValueType: string; ValueName: "Version"; ValueData: "{#AppVersion}"; \
  Components: main

; ── Code ──────────────────────────────────────────────────────────────────────
[Code]

{ Check if VB-Cable is already installed by looking for its device in registry }
function VBCableInstalled: Boolean;
var
  Found: Boolean;
begin
  Found := RegKeyExists(HKLM, 'SYSTEM\CurrentControlSet\Services\VBAudioVACMM');
  if not Found then
    Found := RegKeyExists(HKLM, 'SYSTEM\CurrentControlSet\Services\VBCable');
  Result := Found;
end;

{ Custom install page: show VB-Cable already installed notice }
procedure InitializeWizard;
begin
  if VBCableInstalled then begin
    MsgBox(
      'VB-Audio Virtual Cable is already installed on this system.' + #13#10 +
      'The installer will skip the VB-Cable installation step.',
      mbInformation, MB_OK
    );
  end;
end;

{ Skip VB-Cable install if already present }
function ShouldInstallVBCable: Boolean;
begin
  Result := not VBCableInstalled;
end;

{ Confirm uninstall }
function InitializeUninstall: Boolean;
begin
  Result := MsgBox(
    'Are you sure you want to uninstall {#AppName}?' + #13#10 +
    'This will also remove the Windows Firewall rule for UDP port 55555.',
    mbConfirmation, MB_YESNO
  ) = IDYES;
end;

{ Offer to remove VB-Cable on uninstall }
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;
begin
  if CurUninstallStep = usPostUninstall then begin
    if VBCableInstalled then begin
      if MsgBox(
        'VB-Audio Virtual Cable is still installed.' + #13#10 +
        'Would you like to visit the VB-Audio website to uninstall it manually?',
        mbConfirmation, MB_YESNO
      ) = IDYES then
        ShellExec('open', 'https://vb-audio.com/Cable/', '', '', SW_SHOW, ewNoWait, ResultCode);
    end;
  end;
end;

