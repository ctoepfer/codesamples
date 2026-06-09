package checksum

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestVerifyFileSHA256(t *testing.T) {
	path := filepath.Join(t.TempDir(), "app.zip")
	if err := os.WriteFile(path, []byte("roku beta"), 0o600); err != nil {
		t.Fatal(err)
	}

	err := VerifyFileSHA256(path, "24697daae3b5e5348f9750a093fa32eb18cc2ac77a4469003fa348d609740f02")
	if err != nil {
		t.Fatalf("VerifyFileSHA256 returned error: %v", err)
	}
}

func TestVerifyFileSHA256Mismatch(t *testing.T) {
	path := filepath.Join(t.TempDir(), "app.zip")
	if err := os.WriteFile(path, []byte("roku beta"), 0o600); err != nil {
		t.Fatal(err)
	}

	err := VerifyFileSHA256(path, strings.Repeat("0", 64))
	if err == nil || !strings.Contains(err.Error(), "invalid checksum") {
		t.Fatalf("expected checksum mismatch, got %v", err)
	}
}
