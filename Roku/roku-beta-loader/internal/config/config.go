package config

import (
	"encoding/json"
	"errors"
	"fmt"
	"net/url"
	"os"
	"strings"
)

type Config struct {
	AppName               string `json:"appName"`
	ReleaseManifestURL    string `json:"releaseManifestUrl"`
	SupportURL            string `json:"supportUrl"`
	ExpectedManifestTitle string `json:"expectedManifestTitle"`
	DefaultUsername       string `json:"defaultUsername"`
	DeveloperModeIntro    string `json:"developerModeIntro"`
	PostInstallMessage    string `json:"postInstallMessage"`
}

func Load(path string) (Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return Config{}, fmt.Errorf("read config %q: %w", path, err)
	}

	var cfg Config
	if err := json.Unmarshal(data, &cfg); err != nil {
		return Config{}, fmt.Errorf("parse config %q: %w", path, err)
	}

	if err := cfg.Validate(); err != nil {
		return Config{}, err
	}

	return cfg, nil
}

func (c Config) Validate() error {
	var problems []string
	if strings.TrimSpace(c.AppName) == "" {
		problems = append(problems, "appName is required")
	}
	if err := validateHTTPSURL("releaseManifestUrl", c.ReleaseManifestURL, true); err != nil {
		problems = append(problems, err.Error())
	}
	if err := validateHTTPSURL("supportUrl", c.SupportURL, false); err != nil {
		problems = append(problems, err.Error())
	}
	if strings.TrimSpace(c.DefaultUsername) == "" {
		problems = append(problems, "defaultUsername is required, usually \"rokudev\"")
	}
	if len(problems) > 0 {
		return errors.New(strings.Join(problems, "; "))
	}
	return nil
}

func validateHTTPSURL(field, value string, required bool) error {
	value = strings.TrimSpace(value)
	if value == "" {
		if required {
			return fmt.Errorf("%s is required", field)
		}
		return nil
	}
	parsed, err := url.Parse(value)
	if err != nil || parsed.Scheme == "" || parsed.Host == "" {
		return fmt.Errorf("%s must be a valid URL", field)
	}
	if parsed.Scheme != "https" {
		return fmt.Errorf("%s must use HTTPS", field)
	}
	return nil
}
