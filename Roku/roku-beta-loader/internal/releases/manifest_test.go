package releases

import (
	"strings"
	"testing"
)

func TestDecodeManifest(t *testing.T) {
	body := `{
		"title": "Example Roku Channel",
		"channel": "beta",
		"version": "0.1.0-beta.1",
		"build": 1,
		"published_at": "2026-06-09T10:00:00-07:00",
		"zip_url": "https://example.com/app.zip",
		"sha256": "abc123",
		"notes": ["Initial beta release"]
	}`
	manifest, err := Decode(strings.NewReader(body))
	if err != nil {
		t.Fatalf("Decode returned error: %v", err)
	}
	if manifest.Version != "0.1.0-beta.1" {
		t.Fatalf("unexpected version: %q", manifest.Version)
	}
}

func TestDecodeRejectsHTTPZipURL(t *testing.T) {
	body := `{
		"channel": "beta",
		"version": "0.1.0-beta.1",
		"zip_url": "http://example.com/app.zip",
		"sha256": "abc123"
	}`
	_, err := Decode(strings.NewReader(body))
	if err == nil || !strings.Contains(err.Error(), "zip_url must use HTTPS") {
		t.Fatalf("expected HTTPS validation error, got %v", err)
	}
}
