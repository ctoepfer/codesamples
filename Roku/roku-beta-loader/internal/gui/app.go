//go:build wails

package gui

import (
	"context"
	"strings"
	"sync"
	"time"

	"github.com/ctoepfer/codesamples/Roku/roku-beta-loader/internal/appflow"
	"github.com/ctoepfer/codesamples/Roku/roku-beta-loader/internal/config"
	"github.com/wailsapp/wails/v2/pkg/runtime"
)

// App is the Wails application struct. All exported methods become JS bindings.
type App struct {
	ctx    context.Context
	svc    *appflow.Service
	mu     sync.Mutex
	cfg    config.Config
	cfgSet bool
}

func NewApp(svc *appflow.Service) *App {
	return &App{svc: svc}
}

// Startup is called by Wails after the window is ready.
func (a *App) Startup(ctx context.Context) {
	a.ctx = ctx
}

// LoadConfig opens a file picker (when path is empty) or loads the given path.
// Returns the config fields the UI needs.
func (a *App) LoadConfig(path string) ConfigResult {
	if path == "" {
		chosen, err := runtime.OpenFileDialog(a.ctx, runtime.OpenDialogOptions{
			Title: "Open config file",
			Filters: []runtime.FileFilter{
				{DisplayName: "JSON config (*.json)", Pattern: "*.json"},
			},
		})
		if err != nil || chosen == "" {
			return ConfigResult{Error: "No config file selected."}
		}
		path = chosen
	}

	cfg, err := appflow.LoadConfig(path)
	if err != nil {
		return ConfigResult{Error: "Could not load config: " + err.Error()}
	}

	a.mu.Lock()
	a.cfg = cfg
	a.cfgSet = true
	a.mu.Unlock()

	return a.configResult(cfg, path)
}

// GetConfig returns the currently loaded config, or an error if none is loaded.
// The Path field is empty here because config is held in memory — callers that
// need the path should store it from the original LoadConfig response.
func (a *App) GetConfig() ConfigResult {
	a.mu.Lock()
	defer a.mu.Unlock()
	if !a.cfgSet {
		return ConfigResult{Error: "No config loaded."}
	}
	return a.configResult(a.cfg, "")
}

// DiscoverDevices runs SSDP discovery and returns found Roku devices.
func (a *App) DiscoverDevices() []DeviceResult {
	ctx, cancel := context.WithTimeout(a.ctx, appflow.DiscoverTimeout)
	defer cancel()
	devices, err := a.svc.DiscoverDevices(ctx)
	if err != nil || len(devices) == 0 {
		return []DeviceResult{}
	}
	out := make([]DeviceResult, len(devices))
	for i, d := range devices {
		name := d.Name
		if name == "" {
			name = "Roku (" + d.IP + ")"
		}
		out[i] = DeviceResult{IP: d.IP, Name: name}
	}
	return out
}

// Install runs the full install pipeline for the loaded config.
func (a *App) Install(ip, password string) InstallResult {
	a.mu.Lock()
	if !a.cfgSet {
		a.mu.Unlock()
		return InstallResult{Error: "No config loaded. Please open a config file first."}
	}
	cfg := a.cfg
	a.mu.Unlock()

	ctx, cancel := context.WithTimeout(a.ctx, appflow.InstallTimeout+30*time.Second)
	defer cancel()

	manifest, err := a.svc.InstallLatest(ctx, cfg, ip, password, "")
	if err != nil {
		return InstallResult{Error: friendlyError(err)}
	}
	return InstallResult{OK: true, Version: manifest.Version}
}

func (a *App) configResult(cfg config.Config, path string) ConfigResult {
	label := cfg.InstallButtonLabel
	if label == "" {
		label = "Install Beta"
	}
	return ConfigResult{
		OK:                 true,
		Path:               path,
		AppName:            cfg.AppName,
		DeveloperModeIntro: cfg.DeveloperModeIntro,
		DeveloperModeImage: cfg.DeveloperModeImage,
		ManualIPHelp:       cfg.ManualIPHelp,
		InstallButtonLabel: label,
		PostInstallMessage: cfg.PostInstallMessage,
	}
}

// friendlyError maps internal errors to plain-language messages for the UI.
func friendlyError(err error) string {
	if err == nil {
		return ""
	}
	msg := err.Error()
	switch {
	case strings.Contains(msg, "no such host") || strings.Contains(msg, "connection refused") || strings.Contains(msg, "network unreachable"):
		return "We could not find your Roku. Make sure your computer and Roku are on the same Wi-Fi network."
	case strings.Contains(msg, "401") || strings.Contains(msg, "403") || strings.Contains(msg, "credentials") || strings.Contains(msg, "password"):
		return "The password did not work. Check your Roku developer password and try again."
	case strings.Contains(msg, "timeout") || strings.Contains(msg, "deadline"):
		return "Your computer and Roku may not be on the same Wi-Fi network, or Roku Developer Mode may not be enabled."
	case strings.Contains(msg, "checksum") || strings.Contains(msg, "sha256") || strings.Contains(msg, "verify"):
		return "The beta download could not be verified. Please try again."
	case strings.Contains(msg, "download") || strings.Contains(msg, "manifest") || strings.Contains(msg, "fetch"):
		return "The beta download failed. Check your internet connection and try again."
	default:
		return "Something went wrong. Please try again or contact support."
	}
}
