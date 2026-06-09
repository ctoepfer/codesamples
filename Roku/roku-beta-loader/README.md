# Roku Beta Loader

Roku Beta Loader is a small, configurable utility for helping beta testers
sideload a Roku channel zip before the channel is publicly listed.

The MVP is a CLI-first Go application. The core networking and validation code
is isolated so a Wails desktop UI can be added later without rewriting the
workflow.

## MVP Workflow

1. Load an app-specific JSON config.
2. Fetch the remote release manifest over HTTPS.
3. Download the latest Roku channel zip.
4. Verify the zip with the manifest SHA-256.
5. Guide the tester through enabling Roku Developer Mode manually.
6. Discover Roku devices on the local network with SSDP / ECP.
7. Accept a manual Roku IP address when discovery is blocked.
8. Ask for the Roku developer password without storing it.
9. Upload the zip to the Roku developer installer.
10. Report success or show troubleshooting guidance.

## Roku Developer Mode Limitation

This project does not enable Developer Mode for the user and must not try to
bypass Roku's process. The tester enables Developer Mode manually with the Roku
remote, accepts Roku's prompts, and sets a developer web server password on the
device.

The default developer username is usually `rokudev`. Installing a beta channel
replaces any existing sideloaded app because Roku allows only one sideloaded
channel at a time.

## CLI

From this directory:

```sh
go test ./...
go run ./cmd/roku-beta-loader config validate --config config.example.json
go run ./cmd/roku-beta-loader release check --config config.example.json
go run ./cmd/roku-beta-loader roku discover
go run ./cmd/roku-beta-loader install --config config.example.json --ip 192.168.1.123 --password YOUR_DEV_PASSWORD
```

Build a local binary:

```sh
go build ./cmd/roku-beta-loader
```

## Configuration

```json
{
  "appName": "Example Roku Channel Beta",
  "releaseManifestUrl": "https://example.com/roku/beta/latest.json",
  "supportUrl": "https://example.com/support",
  "expectedManifestTitle": "Example Roku Channel",
  "defaultUsername": "rokudev",
  "developerModeIntro": "",
  "postInstallMessage": ""
}
```

Application-specific values live in JSON. Roku behavior belongs under
`internal/roku`, release and checksum behavior are reusable, and the future
desktop UI should call these same packages.

`developerModeIntro` and `postInstallMessage` are optional app-specific guidance
strings. They are intended for CLI/UI copy that should vary by beta program
without being hardcoded in Go source.

## Release Manifest

```json
{
  "title": "Example Roku Channel",
  "channel": "beta",
  "version": "0.1.0-beta.1",
  "build": 1,
  "published_at": "2026-06-09T10:00:00-07:00",
  "zip_url": "https://example.com/roku/beta/example-roku-channel-0.1.0-beta.1.zip",
  "sha256": "REPLACE_WITH_SHA256",
  "notes": [
    "Initial beta release"
  ]
}
```

`title` is optional for generic manifests, but when present it can be checked
against `expectedManifestTitle` to catch misconfigured URLs.

## Troubleshooting Themes

- Roku is not in Developer Mode.
- The developer password is wrong.
- The computer and Roku are not on the same network.
- A VPN, firewall, or guest Wi-Fi network is blocking discovery.
- The download failed or the checksum does not match.
- Another sideloaded app was replaced by the beta install.

## Example: Iokom Signage

An Iokom Signage example config is included at
`configs/iokom-signage.example.json`. It is only an example of how an
app-specific beta channel can provide its own manifest URL, support URL,
expected manifest title, developer username, and post-install guidance.
