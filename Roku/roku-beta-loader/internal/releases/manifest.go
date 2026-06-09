package releases

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"
)

type Manifest struct {
	Title       string   `json:"title,omitempty"`
	Channel     string   `json:"channel"`
	Version     string   `json:"version"`
	Build       int      `json:"build"`
	PublishedAt string   `json:"published_at"`
	ZipURL      string   `json:"zip_url"`
	SHA256      string   `json:"sha256"`
	Notes       []string `json:"notes"`
}

func Fetch(ctx context.Context, client *http.Client, manifestURL string) (Manifest, error) {
	if client == nil {
		client = &http.Client{Timeout: 20 * time.Second}
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, manifestURL, nil)
	if err != nil {
		return Manifest{}, fmt.Errorf("create manifest request: %w", err)
	}
	resp, err := client.Do(req)
	if err != nil {
		return Manifest{}, fmt.Errorf("fetch release manifest: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode > 299 {
		return Manifest{}, fmt.Errorf("fetch release manifest: server returned %s", resp.Status)
	}
	return Decode(resp.Body)
}

func Decode(r io.Reader) (Manifest, error) {
	var manifest Manifest
	dec := json.NewDecoder(r)
	dec.DisallowUnknownFields()
	if err := dec.Decode(&manifest); err != nil {
		return Manifest{}, fmt.Errorf("parse release manifest: %w", err)
	}
	if err := manifest.Validate(); err != nil {
		return Manifest{}, err
	}
	return manifest, nil
}

func (m Manifest) Validate() error {
	var problems []string
	if strings.TrimSpace(m.Channel) == "" {
		problems = append(problems, "channel is required")
	}
	if strings.TrimSpace(m.Version) == "" {
		problems = append(problems, "version is required")
	}
	if strings.TrimSpace(m.ZipURL) == "" {
		problems = append(problems, "zip_url is required")
	} else if err := validateHTTPSURL("zip_url", m.ZipURL); err != nil {
		problems = append(problems, err.Error())
	}
	if strings.TrimSpace(m.SHA256) == "" {
		problems = append(problems, "sha256 is required")
	}
	if m.PublishedAt != "" {
		if _, err := time.Parse(time.RFC3339, m.PublishedAt); err != nil {
			problems = append(problems, "published_at must be RFC3339")
		}
	}
	if len(problems) > 0 {
		return errors.New(strings.Join(problems, "; "))
	}
	return nil
}

func validateHTTPSURL(field, value string) error {
	parsed, err := url.Parse(value)
	if err != nil || parsed.Scheme == "" || parsed.Host == "" {
		return fmt.Errorf("%s must be a valid URL", field)
	}
	if parsed.Scheme != "https" {
		return fmt.Errorf("%s must use HTTPS", field)
	}
	return nil
}
