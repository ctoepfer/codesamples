package config

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestLoadValidConfig(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "config.json")
	body := `{
		"appName": "Iokom Signage Beta",
		"releaseManifestUrl": "https://example.com/latest.json",
		"supportUrl": "https://example.com/support",
		"expectedManifestTitle": "Iokom Signage",
		"defaultUsername": "rokudev"
	}`
	if err := os.WriteFile(path, []byte(body), 0o600); err != nil {
		t.Fatal(err)
	}

	cfg, err := Load(path)
	if err != nil {
		t.Fatalf("Load returned error: %v", err)
	}
	if cfg.AppName != "Iokom Signage Beta" {
		t.Fatalf("unexpected appName: %q", cfg.AppName)
	}
}

func TestValidateRequiresHTTPSManifest(t *testing.T) {
	cfg := Config{
		AppName:            "Beta",
		ReleaseManifestURL: "http://example.com/latest.json",
		DefaultUsername:    "rokudev",
	}
	err := cfg.Validate()
	if err == nil || !strings.Contains(err.Error(), "releaseManifestUrl must use HTTPS") {
		t.Fatalf("expected HTTPS validation error, got %v", err)
	}
}
