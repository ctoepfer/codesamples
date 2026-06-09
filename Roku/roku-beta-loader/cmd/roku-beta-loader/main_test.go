package main

import (
	"bytes"
	"context"
	"errors"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/ctoepfer/codesamples/Roku/roku-beta-loader/internal/discovery"
	"github.com/ctoepfer/codesamples/Roku/roku-beta-loader/internal/releases"
	"github.com/ctoepfer/codesamples/Roku/roku-beta-loader/internal/roku"
)

type fakeInstaller struct {
	target roku.Target
	err    error
}

func (f *fakeInstaller) Install(_ context.Context, target roku.Target, _ string) error {
	f.target = target
	return f.err
}

func TestInstallPassesDefaultUsername(t *testing.T) {
	cfgPath := writeConfig(t, `"defaultUsername": "test-user"`)
	installer := &fakeInstaller{}
	var out bytes.Buffer

	err := runWithDeps([]string{"install", "--config", cfgPath, "--ip", "192.168.1.123", "--password", "secret"}, installDeps(&out, installer))
	if err != nil {
		t.Fatalf("runWithDeps returned error: %v", err)
	}
	if installer.target.Username != "test-user" {
		t.Fatalf("installer username = %q, want test-user", installer.target.Username)
	}
}

func TestInstallPrintsPostInstallMessage(t *testing.T) {
	cfgPath := writeConfig(t, `"postInstallMessage": "Open the beta channel to finish setup."`)
	var out bytes.Buffer

	err := runWithDeps([]string{"install", "--config", cfgPath, "--ip", "192.168.1.123", "--password", "secret"}, installDeps(&out, &fakeInstaller{}))
	if err != nil {
		t.Fatalf("runWithDeps returned error: %v", err)
	}
	if !strings.Contains(out.String(), "Open the beta channel to finish setup.") {
		t.Fatalf("postInstallMessage missing from output: %s", out.String())
	}
}

func TestInstallPostInstallMessageOptional(t *testing.T) {
	cfgPath := writeConfig(t, "")
	var out bytes.Buffer

	err := runWithDeps([]string{"install", "--config", cfgPath, "--ip", "192.168.1.123", "--password", "secret"}, installDeps(&out, &fakeInstaller{}))
	if err != nil {
		t.Fatalf("runWithDeps returned error: %v", err)
	}
	if strings.Contains(out.String(), "finish setup") {
		t.Fatalf("unexpected post-install message: %s", out.String())
	}
}

func TestSupportURLInReleaseError(t *testing.T) {
	cfgPath := writeConfig(t, `"supportUrl": "https://example.com/support"`)
	deps := defaultDeps(ioDiscard{})
	deps.fetch = func(context.Context, *http.Client, string) (releases.Manifest, error) {
		return releases.Manifest{}, errors.New("release service unavailable")
	}

	err := runWithDeps([]string{"release", "check", "--config", cfgPath}, deps)
	if err == nil || !strings.Contains(err.Error(), "For help, see: https://example.com/support") {
		t.Fatalf("support URL missing from release error: %v", err)
	}
}

func TestSupportURLInInstallTroubleshootingErrors(t *testing.T) {
	cases := []struct {
		name    string
		patch   func(appDeps)
		deps    func(*bytes.Buffer) appDeps
		wantErr string
	}{
		{
			name: "download",
			deps: func(out *bytes.Buffer) appDeps {
				d := installDeps(out, &fakeInstaller{})
				d.download = func(context.Context, *http.Client, string, string) (string, error) {
					return "", errors.New("download failed")
				}
				return d
			},
			wantErr: "For help, see: https://example.com/support",
		},
		{
			name: "checksum",
			deps: func(out *bytes.Buffer) appDeps {
				d := installDeps(out, &fakeInstaller{})
				d.verify = func(string, string) error {
					return errors.New("invalid checksum")
				}
				return d
			},
			wantErr: "For help, see: https://example.com/support",
		},
		{
			name: "install",
			deps: func(out *bytes.Buffer) appDeps {
				return installDeps(out, &fakeInstaller{err: errors.New("install failed")})
			},
			wantErr: "For help, see: https://example.com/support",
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			cfgPath := writeConfig(t, `"supportUrl": "https://example.com/support"`)
			var out bytes.Buffer
			err := runWithDeps([]string{"install", "--config", cfgPath, "--ip", "192.168.1.123", "--password", "secret"}, tc.deps(&out))
			if err == nil || !strings.Contains(err.Error(), tc.wantErr) {
				t.Fatalf("support URL missing from error: %v", err)
			}
		})
	}
}

func TestSupportURLInNoRokuFoundOutput(t *testing.T) {
	cfgPath := writeConfig(t, `"supportUrl": "https://example.com/support"`)
	var out bytes.Buffer
	deps := defaultDeps(&out)
	deps.discover = func(context.Context) ([]discovery.Device, error) {
		return nil, nil
	}

	err := runWithDeps([]string{"roku", "discover", "--config", cfgPath}, deps)
	if err != nil {
		t.Fatalf("runWithDeps returned error: %v", err)
	}
	if !strings.Contains(out.String(), "For help, see: https://example.com/support") {
		t.Fatalf("support URL missing from discover output: %s", out.String())
	}
}

func installDeps(out *bytes.Buffer, installer roku.Installer) appDeps {
	deps := defaultDeps(out)
	deps.fetch = func(context.Context, *http.Client, string) (releases.Manifest, error) {
		return releases.Manifest{
			Channel: "beta",
			Version: "0.1.0-beta.1",
			ZipURL:  "https://example.com/channel.zip",
			SHA256:  strings.Repeat("a", 64),
		}, nil
	}
	deps.download = func(context.Context, *http.Client, string, string) (string, error) {
		return filepath.Join(os.TempDir(), "channel.zip"), nil
	}
	deps.verify = func(string, string) error {
		return nil
	}
	deps.installer = installer
	return deps
}

func writeConfig(t *testing.T, extra string) string {
	t.Helper()
	lines := []string{
		`"appName": "Example Roku Channel Beta"`,
		`"releaseManifestUrl": "https://example.com/roku/beta/latest.json"`,
		`"expectedManifestTitle": "Example Roku Channel"`,
		`"defaultUsername": "rokudev"`,
	}
	if extra != "" {
		lines = append(lines, extra)
	}
	path := filepath.Join(t.TempDir(), "config.json")
	if err := os.WriteFile(path, []byte("{\n"+strings.Join(lines, ",\n")+"\n}"), 0o600); err != nil {
		t.Fatal(err)
	}
	return path
}

type ioDiscard struct{}

func (ioDiscard) Write(p []byte) (int, error) {
	return len(p), nil
}
