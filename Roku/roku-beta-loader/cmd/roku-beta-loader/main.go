package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"time"

	"github.com/ctoepfer/codesamples/Roku/roku-beta-loader/internal/checksum"
	"github.com/ctoepfer/codesamples/Roku/roku-beta-loader/internal/config"
	"github.com/ctoepfer/codesamples/Roku/roku-beta-loader/internal/discovery"
	"github.com/ctoepfer/codesamples/Roku/roku-beta-loader/internal/releases"
	"github.com/ctoepfer/codesamples/Roku/roku-beta-loader/internal/roku"
)

func main() {
	if err := run(os.Args[1:]); err != nil {
		fmt.Fprintln(os.Stderr, "Error:", err)
		os.Exit(1)
	}
}

func run(args []string) error {
	return runWithDeps(args, defaultDeps(os.Stdout))
}

type appDeps struct {
	stdout       io.Writer
	fetch        func(context.Context, *http.Client, string) (releases.Manifest, error)
	download     func(context.Context, *http.Client, string, string) (string, error)
	verify       func(string, string) error
	discover     func(context.Context) ([]discovery.Device, error)
	installer    roku.Installer
	manifestHTTP *http.Client
	downloadHTTP *http.Client
}

func defaultDeps(stdout io.Writer) appDeps {
	return appDeps{
		stdout:       stdout,
		fetch:        releases.Fetch,
		download:     releases.DownloadZip,
		verify:       checksum.VerifyFileSHA256,
		discover:     discovery.Discover,
		installer:    roku.HTTPInstaller{},
		manifestHTTP: http.DefaultClient,
		downloadHTTP: http.DefaultClient,
	}
}

func runWithDeps(args []string, deps appDeps) error {
	if deps.stdout == nil {
		deps.stdout = io.Discard
	}
	if len(args) == 0 {
		return usage(deps.stdout)
	}

	switch args[0] {
	case "config":
		return runConfig(args[1:], deps)
	case "release":
		return runRelease(args[1:], deps)
	case "roku":
		return runRoku(args[1:], deps)
	case "install":
		return runInstall(args[1:], deps)
	case "version", "--version", "-v":
		fmt.Fprintln(deps.stdout, "roku-beta-loader "+version)
		return nil
	case "help", "-h", "--help":
		return usage(deps.stdout)
	default:
		return fmt.Errorf("unknown command %q\n\n%w", args[0], errUsage)
	}
}

func runConfig(args []string, deps appDeps) error {
	if len(args) == 0 || args[0] != "validate" {
		return errors.New("usage: roku-beta-loader config validate --config PATH")
	}
	fs := flag.NewFlagSet("config validate", flag.ContinueOnError)
	configPath := fs.String("config", "", "Path to JSON config")
	if err := fs.Parse(args[1:]); err != nil {
		return err
	}
	cfg, err := loadConfig(*configPath)
	if err != nil {
		return err
	}
	fmt.Fprintf(deps.stdout, "Config OK: %s\n", cfg.AppName)
	return nil
}

func runRelease(args []string, deps appDeps) error {
	if len(args) == 0 || args[0] != "check" {
		return errors.New("usage: roku-beta-loader release check --config PATH")
	}
	fs := flag.NewFlagSet("release check", flag.ContinueOnError)
	configPath := fs.String("config", "", "Path to JSON config")
	if err := fs.Parse(args[1:]); err != nil {
		return err
	}
	cfg, err := loadConfig(*configPath)
	if err != nil {
		return err
	}
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	manifest, err := deps.fetch(ctx, deps.manifestHTTP, cfg.ReleaseManifestURL)
	if err != nil {
		return withSupport(err, cfg)
	}
	if err := checkManifestTitle(cfg, manifest); err != nil {
		return err
	}
	fmt.Fprintf(deps.stdout, "Release OK: %s %s build %d\n", cfg.AppName, manifest.Version, manifest.Build)
	fmt.Fprintf(deps.stdout, "Zip: %s\n", manifest.ZipURL)
	return nil
}

func runRoku(args []string, deps appDeps) error {
	if len(args) == 0 || args[0] != "discover" {
		return errors.New("usage: roku-beta-loader roku discover [--config PATH]")
	}
	fs := flag.NewFlagSet("roku discover", flag.ContinueOnError)
	configPath := fs.String("config", "", "Optional path to JSON config for support URL")
	if err := fs.Parse(args[1:]); err != nil {
		return err
	}
	var cfg config.Config
	if *configPath != "" {
		loaded, err := loadConfig(*configPath)
		if err != nil {
			return err
		}
		cfg = loaded
	}
	ctx, cancel := context.WithTimeout(context.Background(), 4*time.Second)
	defer cancel()
	devices, err := deps.discover(ctx)
	if err != nil {
		return withSupport(err, cfg)
	}
	if len(devices) == 0 {
		fmt.Fprintln(deps.stdout, supportLine("No Roku devices found. Try manual IP entry, and check same-network, VPN, firewall, and guest Wi-Fi settings.", cfg))
		return nil
	}
	for _, device := range devices {
		fmt.Fprintf(deps.stdout, "%s\t%s\t%s\n", device.IP, device.USN, device.Location)
	}
	return nil
}

func runInstall(args []string, deps appDeps) error {
	fs := flag.NewFlagSet("install", flag.ContinueOnError)
	configPath := fs.String("config", "", "Path to JSON config")
	ip := fs.String("ip", "", "Roku IP address")
	password := fs.String("password", "", "Roku developer password")
	outDir := fs.String("download-dir", "", "Directory for temporary zip download")
	if err := fs.Parse(args); err != nil {
		return err
	}
	cfg, err := loadConfig(*configPath)
	if err != nil {
		return err
	}
	if *ip == "" {
		return errors.New("Roku IP is required. Run `roku-beta-loader roku discover` or enter the Roku IP manually")
	}
	if *password == "" {
		return errors.New("Roku developer password is required. This tool does not store passwords by default")
	}
	if cfg.DeveloperModeIntro != "" {
		fmt.Fprintln(deps.stdout, cfg.DeveloperModeIntro)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Minute)
	defer cancel()

	manifest, err := deps.fetch(ctx, deps.manifestHTTP, cfg.ReleaseManifestURL)
	if err != nil {
		return withSupport(err, cfg)
	}
	if err := checkManifestTitle(cfg, manifest); err != nil {
		return err
	}
	zipPath, err := deps.download(ctx, deps.downloadHTTP, manifest.ZipURL, *outDir)
	if err != nil {
		return withSupport(err, cfg)
	}
	if err := deps.verify(zipPath, manifest.SHA256); err != nil {
		return withSupport(err, cfg)
	}

	err = deps.installer.Install(ctx, roku.Target{
		IP:       *ip,
		Username: cfg.DefaultUsername,
		Password: *password,
	}, zipPath)
	if err != nil {
		return withSupport(err, cfg)
	}
	fmt.Fprintf(deps.stdout, "Install complete: %s %s\n", cfg.AppName, manifest.Version)
	fmt.Fprintln(deps.stdout, "The beta replaced any previous sideloaded channel on this Roku.")
	if cfg.PostInstallMessage != "" {
		fmt.Fprintln(deps.stdout, cfg.PostInstallMessage)
	}
	return nil
}

func loadConfig(path string) (config.Config, error) {
	if path == "" {
		return config.Config{}, errors.New("--config PATH is required")
	}
	return config.Load(path)
}

func checkManifestTitle(cfg config.Config, manifest releases.Manifest) error {
	if cfg.ExpectedManifestTitle == "" || manifest.Title == "" {
		return nil
	}
	if manifest.Title != cfg.ExpectedManifestTitle {
		return fmt.Errorf("release manifest title %q did not match expected title %q", manifest.Title, cfg.ExpectedManifestTitle)
	}
	return nil
}

// version is "dev" for local builds and is overridden at release time via the
// build scripts with -ldflags "-X main.version=...".
var version = "dev"

var errUsage = errors.New("usage: roku-beta-loader <config|release|roku|install>")

func usage(w io.Writer) error {
	fmt.Fprintln(w, `Usage:
  roku-beta-loader config validate --config PATH
  roku-beta-loader release check --config PATH
  roku-beta-loader roku discover
  roku-beta-loader install --config PATH --ip ROKU_IP --password PASSWORD`)
	return nil
}

func withSupport(err error, cfg config.Config) error {
	if cfg.SupportURL == "" {
		return err
	}
	return fmt.Errorf("%w\nFor help, see: %s", err, cfg.SupportURL)
}

func supportLine(message string, cfg config.Config) string {
	if cfg.SupportURL == "" {
		return message
	}
	return message + "\nFor help, see: " + cfg.SupportURL
}
