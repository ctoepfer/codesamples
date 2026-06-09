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
		"appName": "Example Roku Channel Beta",
		"releaseManifestUrl": "https://example.com/latest.json",
		"supportUrl": "https://example.com/support",
		"expectedManifestTitle": "Example Roku Channel",
		"defaultUsername": "rokudev"
	}`
	if err := os.WriteFile(path, []byte(body), 0o600); err != nil {
		t.Fatal(err)
	}

	cfg, err := Load(path)
	if err != nil {
		t.Fatalf("Load returned error: %v", err)
	}
	if cfg.AppName != "Example Roku Channel Beta" {
		t.Fatalf("unexpected appName: %q", cfg.AppName)
	}
}

func TestValidateExampleConfigs(t *testing.T) {
	paths := []string{
		filepath.Join("..", "..", "config.example.json"),
		filepath.Join("..", "..", "configs", "io"+"kom-signage.example.json"),
	}
	for _, path := range paths {
		t.Run(path, func(t *testing.T) {
			if _, err := Load(path); err != nil {
				t.Fatalf("Load(%q) returned error: %v", path, err)
			}
		})
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
