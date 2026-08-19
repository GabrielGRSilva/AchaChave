; ============================================================
;  AchaChave - Script de Instalador (Inno Setup 6)
;  Gera: AchaChave_Instalador.exe
; ============================================================

#define MyAppName      "AchaChave"
#define MyAppVersion   "1.2"
#define MyAppPublisher "AchaChave"
#define MyAppExeName   "AchaChave.exe"
#define DistDir        "dist"
#define TesseractInst  "installer_tools\tesseract-installer.exe"

[Setup]
AppId={{F3A2C8D1-5E4B-4A7F-9C3D-2B1E6F8A0D5C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=.
OutputBaseFilename=AchaChave_Instalador
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; Não requer privilégios de administrador (instala para o usuário atual)
PrivilegesRequired=lowest

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na Área de Trabalho"; GroupDescription: "Atalhos:"

[Files]
; Todos os arquivos do aplicativo (compilados pelo PyInstaller)
Source: "{#DistDir}\AchaChave.exe"; DestDir: "{app}"; Flags: ignoreversion

; Instalador do Tesseract OCR (embutido no instalador)
Source: "{#TesseractInst}"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
; Atalho no Menu Iniciar
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"

; Atalho na Área de Trabalho (opcional)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Instala o Tesseract OCR silenciosamente ANTES de finalizar
; O Check: evita instalar de novo se o Tesseract já estiver presente
Filename: "{tmp}\tesseract-installer.exe"; \
    Parameters: "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-"; \
    StatusMsg: "Instalando Tesseract OCR (suporte a imagens)..."; \
    Check: not TesseractAlreadyInstalled; \
    Flags: runhidden

; Abre o aplicativo ao finalizar a instalação (opcional, marcado por padrão)
Filename: "{app}\{#MyAppExeName}"; \
    Description: "Abrir {#MyAppName} agora"; \
    Flags: nowait postinstall skipifsilent

[UninstallRun]
; Não desinstala o Tesseract automaticamente (pode ser usado por outros apps)
; O usuário pode desinstalar pelo Painel de Controle se quiser.

[Code]
// Verifica se o Tesseract já está instalado para não instalar duplicado
function TesseractAlreadyInstalled: Boolean;
var
  TesseractPath: String;
begin
  Result := RegQueryStringValue(HKLM, 'SOFTWARE\Tesseract-OCR', 'InstallDir', TesseractPath) or
            RegQueryStringValue(HKCU, 'SOFTWARE\Tesseract-OCR', 'InstallDir', TesseractPath);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssInstall) and TesseractAlreadyInstalled then
    Log('Tesseract OCR ja esta instalado. Instalacao ignorada.');
end;
