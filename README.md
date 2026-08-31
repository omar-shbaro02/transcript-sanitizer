# Transcript Sanitizer

Transcript Sanitizer is a local-only desktop utility for cleaning and anonymizing confidential meeting transcripts before they are reviewed or used elsewhere.

It supports `.txt` and `.docx` input, preserves transcript structure, and outputs an anonymized transcript, a processing report, and an optional local mapping file.

## Privacy Guarantee

This app does not use AI APIs, OpenAI, cloud sync, analytics, telemetry, backend servers, embeddings, or vector databases. Processing runs locally on your computer.

The build scripts download Python dependencies and the spaCy model while creating the installer. After installation, transcript processing itself is local and offline.

## Important Limits

Automated anonymization is not perfect. Always manually review the anonymized transcript before uploading it to any external AI tool or sharing it outside your organization.

Never upload files from `local_maps/` to an external AI tool. Mapping files can reveal the original names and identifiers.

## Client Install

Windows clients should download `TranscriptSanitizerSetup.exe` from the GitHub Release and run it. The installer places the app in Program Files, creates a Start Menu shortcut, offers an optional Desktop shortcut, and supports uninstall from Windows Apps & Features.

macOS clients should download `TranscriptSanitizer-macOS.pkg` from the GitHub Release and run it. New release packages produced after the signing setup below is configured are signed with an Apple Developer ID, notarized by Apple, and have the notarization ticket stapled.

Clients do not need to install Python, pip, spaCy, Presidio, or any Python libraries manually.

## Developer Install

Install Python 3.11 or newer, then run:

```bat
cd transcript-sanitizer
pip install -r requirements.txt
python -m spacy download en_core_web_lg
```

If the large spaCy model is unavailable, install the smaller fallback model:

```bat
python -m spacy download en_core_web_sm
```

## Run Desktop App

```bat
python app.py
```

The UI lets you select a transcript, choose anonymization options, process locally, and open the output folder.

## Run CLI

```bat
python app.py --input input\meeting.txt --output output\ --config config\default_config.json
```

Optional CLI flags:

```bat
python app.py --input input\meeting.txt --output output\ --anonymize-dates
python app.py --input input\meeting.txt --output output\ --no-map
```

## Build Windows EXE

```bat
packaging\build_exe.bat
```

The executable folder is created by PyInstaller under `dist\TranscriptSanitizer\`.

## Build Windows Installer

Install Inno Setup 6, then run:

```bat
packaging\build_installer.bat
```

The installer is created at `dist\installer\TranscriptSanitizerSetup.exe`.

## Build macOS App and Installer

Run these commands on macOS:

```bash
chmod +x packaging/build_mac_app.sh packaging/build_mac_pkg.sh
packaging/build_mac_app.sh
packaging/build_mac_pkg.sh
```

The app is created at `dist/TranscriptSanitizer.app` and the installer at `dist/TranscriptSanitizer-macOS.pkg`.

## GitHub Release Builds

Pushing a release tag such as `v1.0.0` triggers two GitHub Actions workflows:

- Windows builds `TranscriptSanitizerSetup.exe` on a Windows runner.
- macOS builds `TranscriptSanitizer-macOS.pkg` on a macOS runner.

Both installers are uploaded as assets on the GitHub Release for that tag.

### Release signing setup

Release builds intentionally fail if signing credentials are missing; this prevents an unsigned installer from being published accidentally.

For macOS, enroll in the Apple Developer Program and export the `Developer ID Application` and `Developer ID Installer` certificates (including their private keys) to one password-protected `.p12`. Add these GitHub Actions repository secrets:

- `APPLE_CERTIFICATE_BASE64`: base64 contents of the `.p12` file
- `APPLE_CERTIFICATE_PASSWORD`: password used when exporting the `.p12`
- `MACOS_APPLICATION_IDENTITY`: full certificate name, such as `Developer ID Application: Company Name (TEAMID)`
- `MACOS_INSTALLER_IDENTITY`: full certificate name, such as `Developer ID Installer: Company Name (TEAMID)`
- `APPLE_ID`: Apple ID used for notarization
- `APPLE_TEAM_ID`: ten-character Apple Developer team ID
- `APPLE_APP_SPECIFIC_PASSWORD`: app-specific password created for the Apple ID

For Windows, obtain an Authenticode code-signing certificate whose provider supports a password-protected `.pfx`, then add:

- `WINDOWS_CERTIFICATE_BASE64`: base64 contents of the `.pfx` file
- `WINDOWS_CERTIFICATE_PASSWORD`: password for the `.pfx`

Many newly issued Windows certificates use a hardware token or cloud signing service instead of an exportable `.pfx`. If your certificate provider requires that model, replace the two SignTool steps with the provider's GitHub Actions integration; do not try to export a protected private key.

On macOS, generate base64 without line wrapping with `base64 -i certificate.p12 | pbcopy`. On PowerShell, use `[Convert]::ToBase64String([IO.File]::ReadAllBytes("certificate.pfx"))` and copy the output. Never commit either certificate file or its password.

After configuring the secrets, create and push a new version tag. Existing GitHub Release assets remain unsigned and must be replaced by artifacts from the new workflow run.

## Configuration

Edit `config/default_config.json` to control behavior:

```json
{
  "anonymize_dates": false,
  "anonymize_locations": true,
  "anonymize_organizations": true,
  "save_local_mapping": true,
  "mapping_file_warning": true,
  "custom_sensitive_terms": [],
  "client_names": [],
  "company_names": [],
  "known_people": [],
  "output_format": "txt"
}
```

Use `custom_sensitive_terms`, `client_names`, `company_names`, and `known_people` for project-specific terms that automated detectors might miss.

## Outputs

For each processed file, the app writes:

```text
output/originalfilename_anonymized.txt
output/originalfilename_processing_report.json
local_maps/originalfilename_mapping_YYYYMMDD_HHMMSS.json
```

For `.docx` input, the app also writes a simple anonymized `.docx`.

## What It Detects

Transcript Sanitizer combines local Presidio detection, local spaCy NER, config terms, and regex patterns for emails, phone numbers, URLs, IDs, speaker names, organizations, locations, and optional dates.

When multiple detectors overlap, the app keeps the longer and more specific match.
