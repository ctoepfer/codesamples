package appflow

import (
	"context"
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/ctoepfer/codesamples/Roku/roku-beta-loader/internal/checksum"
	"github.com/ctoepfer/codesamples/Roku/roku-beta-loader/internal/config"
	"github.com/ctoepfer/codesamples/Roku/roku-beta-loader/internal/discovery"
	"github.com/ctoepfer/codesamples/Roku/roku-beta-loader/internal/releases"
	"github.com/ctoepfer/codesamples/Roku/roku-beta-loader/internal/roku"
)

// Deps holds the injectable dependencies used by Service.
type Deps struct {
	Fetch        func(context.Context, *http.Client, string) (releases.Manifest, error)
	Download     func(context.Context, *http.Client, string, string) (string, error)
	Verify       func(string, string) error
	Discover     func(context.Context) ([]discovery.Device, error)
	Installer    roku.Installer
	ManifestHTTP *http.Client
	DownloadHTTP *http.Client
}

// Service orchestrates the install pipeline. Construct with New or NewWithDeps.
type Service struct {
	deps Deps
}

func New() *Service {
	return NewWithDeps(defaultDeps())
}

func NewWithDeps(deps Deps) *Service {
	return &Service{deps: deps}
}

func defaultDeps() Deps {
	return Deps{
		Fetch:        releases.Fetch,
		Download:     releases.DownloadZip,
		Verify:       checksum.VerifyFileSHA256,
		Discover:     discovery.Discover,
		Installer:    roku.HTTPInstaller{},
		ManifestHTTP: http.DefaultClient,
		DownloadHTTP: http.DefaultClient,
	}
}

func LoadConfig(path string) (config.Config, error) {
	return config.Load(path)
}

// CheckRelease fetches the release manifest and validates the title against cfg.
func (s *Service) CheckRelease(ctx context.Context, cfg config.Config) (releases.Manifest, error) {
	manifest, err := s.deps.Fetch(ctx, s.deps.ManifestHTTP, cfg.ReleaseManifestURL)
	if err != nil {
		return releases.Manifest{}, err
	}
	if err := checkManifestTitle(cfg, manifest); err != nil {
		return releases.Manifest{}, err
	}
	return manifest, nil
}

// DownloadRelease downloads the zip from manifest.ZipURL and verifies its SHA-256.
// destDir is the directory for the temporary file; pass "" for os.TempDir().
func (s *Service) DownloadRelease(ctx context.Context, manifest releases.Manifest, destDir string) (string, error) {
	zipPath, err := s.deps.Download(ctx, s.deps.DownloadHTTP, manifest.ZipURL, destDir)
	if err != nil {
		return "", err
	}
	if err := s.deps.Verify(zipPath, manifest.SHA256); err != nil {
		return "", err
	}
	return zipPath, nil
}

// DiscoverDevices runs SSDP discovery and returns found Roku devices.
func (s *Service) DiscoverDevices(ctx context.Context) ([]discovery.Device, error) {
	return s.deps.Discover(ctx)
}

// InstallLatest runs the full pipeline: fetch manifest, download zip, verify,
// and upload to the Roku at ip. destDir may be "" to use os.TempDir().
func (s *Service) InstallLatest(ctx context.Context, cfg config.Config, ip, password, destDir string) (releases.Manifest, error) {
	if strings.TrimSpace(ip) == "" {
		return releases.Manifest{}, fmt.Errorf("Roku IP address is required")
	}
	if password == "" {
		return releases.Manifest{}, fmt.Errorf("Roku developer password is required")
	}

	manifest, err := s.CheckRelease(ctx, cfg)
	if err != nil {
		return releases.Manifest{}, err
	}
	zipPath, err := s.DownloadRelease(ctx, manifest, destDir)
	if err != nil {
		return releases.Manifest{}, err
	}
	if err := s.InstallZip(ctx, cfg, ip, password, zipPath); err != nil {
		return releases.Manifest{}, err
	}
	return manifest, nil
}

// InstallZip uploads an already-downloaded zip to the Roku at ip.
func (s *Service) InstallZip(ctx context.Context, cfg config.Config, ip, password, zipPath string) error {
	return s.deps.Installer.Install(ctx, roku.Target{
		IP:       ip,
		Username: cfg.DefaultUsername,
		Password: password,
	}, zipPath)
}

// InstallTimeout is the default context timeout for a full install pipeline.
const InstallTimeout = 3 * time.Minute

// DiscoverTimeout is the default context timeout for device discovery.
const DiscoverTimeout = 4 * time.Second

func checkManifestTitle(cfg config.Config, manifest releases.Manifest) error {
	if cfg.ExpectedManifestTitle == "" || manifest.Title == "" {
		return nil
	}
	if manifest.Title != cfg.ExpectedManifestTitle {
		return fmt.Errorf("release manifest title %q did not match expected title %q", manifest.Title, cfg.ExpectedManifestTitle)
	}
	return nil
}
