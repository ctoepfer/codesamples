package appflow_test

import (
	"context"
	"errors"
	"net/http"
	"testing"

	"github.com/ctoepfer/codesamples/Roku/roku-beta-loader/internal/appflow"
	"github.com/ctoepfer/codesamples/Roku/roku-beta-loader/internal/config"
	"github.com/ctoepfer/codesamples/Roku/roku-beta-loader/internal/discovery"
	"github.com/ctoepfer/codesamples/Roku/roku-beta-loader/internal/releases"
	"github.com/ctoepfer/codesamples/Roku/roku-beta-loader/internal/roku"
)

func testCfg() config.Config {
	return config.Config{
		AppName:            "Test Channel Beta",
		ReleaseManifestURL: "https://example.com/latest.json",
		DefaultUsername:    "rokudev",
	}
}

func stubDeps(manifest releases.Manifest, zipPath string, installErr error) appflow.Deps {
	return appflow.Deps{
		Fetch: func(_ context.Context, _ *http.Client, _ string) (releases.Manifest, error) {
			return manifest, nil
		},
		Download: func(_ context.Context, _ *http.Client, _, _ string) (string, error) {
			return zipPath, nil
		},
		Verify: func(_, _ string) error {
			return nil
		},
		Discover: func(_ context.Context) ([]discovery.Device, error) {
			return []discovery.Device{{IP: "192.168.1.100", Name: "Roku"}}, nil
		},
		Installer: stubInstaller{err: installErr},
	}
}

type stubInstaller struct{ err error }

func (s stubInstaller) Install(_ context.Context, _ roku.Target, _ string) error { return s.err }

func TestCheckRelease(t *testing.T) {
	manifest := releases.Manifest{
		Channel: "beta",
		Version: "1.0.0",
		ZipURL:  "https://example.com/app.zip",
		SHA256:  "abc123",
	}
	svc := appflow.NewWithDeps(stubDeps(manifest, "/tmp/app.zip", nil))
	got, err := svc.CheckRelease(context.Background(), testCfg())
	if err != nil {
		t.Fatalf("CheckRelease returned error: %v", err)
	}
	if got.Version != "1.0.0" {
		t.Fatalf("unexpected version: %q", got.Version)
	}
}

func TestCheckReleaseValidatesTitle(t *testing.T) {
	manifest := releases.Manifest{
		Title:   "Wrong Title",
		Channel: "beta",
		Version: "1.0.0",
		ZipURL:  "https://example.com/app.zip",
		SHA256:  "abc123",
	}
	cfg := testCfg()
	cfg.ExpectedManifestTitle = "Expected Title"

	svc := appflow.NewWithDeps(stubDeps(manifest, "/tmp/app.zip", nil))
	_, err := svc.CheckRelease(context.Background(), cfg)
	if err == nil {
		t.Fatal("expected title mismatch error, got nil")
	}
}

func TestDownloadRelease(t *testing.T) {
	manifest := releases.Manifest{
		Channel: "beta",
		Version: "1.0.0",
		ZipURL:  "https://example.com/app.zip",
		SHA256:  "abc123",
	}
	svc := appflow.NewWithDeps(stubDeps(manifest, "/tmp/app.zip", nil))
	path, err := svc.DownloadRelease(context.Background(), manifest, "")
	if err != nil {
		t.Fatalf("DownloadRelease returned error: %v", err)
	}
	if path != "/tmp/app.zip" {
		t.Fatalf("unexpected path: %q", path)
	}
}

func TestDiscoverDevices(t *testing.T) {
	svc := appflow.NewWithDeps(stubDeps(releases.Manifest{}, "", nil))
	devices, err := svc.DiscoverDevices(context.Background())
	if err != nil {
		t.Fatalf("DiscoverDevices returned error: %v", err)
	}
	if len(devices) != 1 || devices[0].IP != "192.168.1.100" {
		t.Fatalf("unexpected devices: %v", devices)
	}
}

func TestInstallLatestSuccess(t *testing.T) {
	manifest := releases.Manifest{
		Channel: "beta",
		Version: "1.0.0",
		ZipURL:  "https://example.com/app.zip",
		SHA256:  "abc123",
	}
	svc := appflow.NewWithDeps(stubDeps(manifest, "/tmp/app.zip", nil))
	got, err := svc.InstallLatest(context.Background(), testCfg(), "192.168.1.100", "secret", "")
	if err != nil {
		t.Fatalf("InstallLatest returned error: %v", err)
	}
	if got.Version != "1.0.0" {
		t.Fatalf("unexpected version: %q", got.Version)
	}
}

func TestInstallLatestRequiresIP(t *testing.T) {
	svc := appflow.NewWithDeps(stubDeps(releases.Manifest{}, "", nil))
	_, err := svc.InstallLatest(context.Background(), testCfg(), "", "secret", "")
	if err == nil {
		t.Fatal("expected error for missing IP, got nil")
	}
}

func TestInstallLatestRequiresPassword(t *testing.T) {
	svc := appflow.NewWithDeps(stubDeps(releases.Manifest{}, "", nil))
	_, err := svc.InstallLatest(context.Background(), testCfg(), "192.168.1.100", "", "")
	if err == nil {
		t.Fatal("expected error for missing password, got nil")
	}
}

func TestInstallLatestPropagatesInstallError(t *testing.T) {
	manifest := releases.Manifest{
		Channel: "beta",
		Version: "1.0.0",
		ZipURL:  "https://example.com/app.zip",
		SHA256:  "abc123",
	}
	installErr := errors.New("Roku rejected credentials")
	svc := appflow.NewWithDeps(stubDeps(manifest, "/tmp/app.zip", installErr))
	_, err := svc.InstallLatest(context.Background(), testCfg(), "192.168.1.100", "wrong", "")
	if err == nil {
		t.Fatal("expected install error, got nil")
	}
}

func TestInstallLatestChecksumFailure(t *testing.T) {
	manifest := releases.Manifest{
		Channel: "beta",
		Version: "1.0.0",
		ZipURL:  "https://example.com/app.zip",
		SHA256:  "abc123",
	}
	deps := appflow.Deps{
		Fetch: func(_ context.Context, _ *http.Client, _ string) (releases.Manifest, error) {
			return manifest, nil
		},
		Download: func(_ context.Context, _ *http.Client, _, _ string) (string, error) {
			return "/tmp/app.zip", nil
		},
		Verify: func(_, _ string) error {
			return errors.New("checksum mismatch")
		},
		Discover:  func(_ context.Context) ([]discovery.Device, error) { return nil, nil },
		Installer: stubInstaller{},
	}
	svc := appflow.NewWithDeps(deps)
	_, err := svc.InstallLatest(context.Background(), testCfg(), "192.168.1.100", "secret", "")
	if err == nil {
		t.Fatal("expected checksum error, got nil")
	}
}
