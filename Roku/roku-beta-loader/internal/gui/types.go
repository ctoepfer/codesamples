//go:build wails

package gui

// ConfigResult carries the config fields the frontend needs.
// Sensitive internals (manifest URL, checksum, port details) are never exposed.
type ConfigResult struct {
	OK                 bool   `json:"ok"`
	Path               string `json:"path"`
	AppName            string `json:"appName"`
	DeveloperModeIntro string `json:"developerModeIntro"`
	DeveloperModeImage string `json:"developerModeImage"`
	ManualIPHelp       string `json:"manualIpHelp"`
	InstallButtonLabel string `json:"installButtonLabel"`
	PostInstallMessage string `json:"postInstallMessage"`
	Error              string `json:"error,omitempty"`
}

// DeviceResult is a Roku device found by discovery.
type DeviceResult struct {
	IP   string `json:"ip"`
	Name string `json:"name"`
}

// InstallResult is the outcome of an install attempt.
type InstallResult struct {
	OK      bool   `json:"ok"`
	Version string `json:"version,omitempty"`
	Error   string `json:"error,omitempty"`
}
