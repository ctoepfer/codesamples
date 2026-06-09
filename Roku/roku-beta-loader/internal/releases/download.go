package releases

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"time"
)

func DownloadZip(ctx context.Context, client *http.Client, zipURL, destDir string) (string, error) {
	if client == nil {
		client = &http.Client{Timeout: 2 * time.Minute}
	}
	if destDir == "" {
		destDir = os.TempDir()
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, zipURL, nil)
	if err != nil {
		return "", fmt.Errorf("create download request: %w", err)
	}
	resp, err := client.Do(req)
	if err != nil {
		return "", fmt.Errorf("download Roku channel zip: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode > 299 {
		return "", fmt.Errorf("download Roku channel zip: server returned %s", resp.Status)
	}

	out, err := os.CreateTemp(destDir, "roku-beta-*.zip")
	if err != nil {
		return "", fmt.Errorf("create temporary zip: %w", err)
	}
	defer out.Close()

	if _, err := io.Copy(out, resp.Body); err != nil {
		return "", fmt.Errorf("write downloaded zip: %w", err)
	}
	if err := out.Sync(); err != nil {
		return "", fmt.Errorf("flush downloaded zip: %w", err)
	}
	return filepath.Abs(out.Name())
}
