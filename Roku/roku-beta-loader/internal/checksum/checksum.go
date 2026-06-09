package checksum

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io"
	"os"
	"strings"
)

func FileSHA256(path string) (string, error) {
	file, err := os.Open(path)
	if err != nil {
		return "", fmt.Errorf("open file for checksum: %w", err)
	}
	defer file.Close()

	sum := sha256.New()
	if _, err := io.Copy(sum, file); err != nil {
		return "", fmt.Errorf("calculate SHA-256: %w", err)
	}
	return hex.EncodeToString(sum.Sum(nil)), nil
}

func VerifyFileSHA256(path, expected string) error {
	actual, err := FileSHA256(path)
	if err != nil {
		return err
	}
	if !strings.EqualFold(actual, strings.TrimSpace(expected)) {
		return fmt.Errorf("invalid checksum: expected %s, got %s", expected, actual)
	}
	return nil
}
