#define MyAppName "Transcript Sanitizer"
#define MyAppExeName "TranscriptSanitizer.exe"
#if GetEnv("APP_VERSION") != ""
#define MyAppVersion GetEnv("APP_VERSION")
#else
#define MyAppVersion "1.0.0"
#endif

[Setup]
AppId={{7F7177D7-08B1-4B4E-85CC-0F72808991D0}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=Transcript Sanitizer
DefaultDirName={autopf}\TranscriptSanitizer
DefaultGroupName=Transcript Sanitizer
DisableProgramGroupPage=yes
LicenseFile=..\README.md
OutputDir=..\dist\installer
OutputBaseFilename=TranscriptSanitizerSetup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\{#MyAppExeName}
#ifexist "app.ico"
SetupIconFile=app.ico
#endif

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\TranscriptSanitizer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README.md"; DestDir: "{app}"; DestName: "README.md"; Flags: ignoreversion

[Icons]
Name: "{group}\Transcript Sanitizer"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\README and Privacy Notice"; Filename: "{app}\README.md"
Name: "{autodesktop}\Transcript Sanitizer"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Transcript Sanitizer"; Flags: nowait postinstall skipifsilent
