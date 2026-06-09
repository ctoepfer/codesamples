package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
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
	if len(args) == 0 {
		return usage()
	}

	switch args[0] {
	case "config":
		return runConfig(args[1:])
	case "release":
		return runRelease(args[1:])
	case "roku":
		return runRoku(args[1:])
	case "install":
		return runInstall(args[1:])
	case "help", "-h", "--help":
		return usage()
	default:
		return fmt.Errorf("unknown command %q\n\n%w", args[0], errUsage)
	}
}

func runConfig(args []string) error {
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
	fmt.Printf("Config OK: %s\n", cfg.AppName)
	return nil
}

func runRelease(args []string) error {
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
	manifest, err := releases.Fetch(ctx, http.DefaultClient, cfg.ReleaseManifestURL)
	if err != nil {
		return err
	}
	if err := checkManifestTitle(cfg, manifest); err != nil {
		return err
	}
	fmt.Printf("Release OK: %s %s build %d\n", cfg.AppName, manifest.Version, manifest.Build)
	fmt.Printf("Zip: %s\n", manifest.ZipURL)
	return nil
}

func runRoku(args []string) error {
	if len(args) == 0 || args[0] != "discover" {
		return errors.New("usage: roku-beta-loader roku discover")
	}
	ctx, cancel := context.WithTimeout(context.Background(), 4*time.Second)
	defer cancel()
	devices, err := discovery.Discover(ctx)
	if err != nil {
		return err
	}
	if len(devices) == 0 {
		fmt.Println("No Roku devices found. Try manual IP entry, and check same-network, VPN, firewall, and guest Wi-Fi settings.")
		return nil
	}
	for _, device := range devices {
		fmt.Printf("%s\t%s\t%s\n", device.IP, device.USN, device.Location)
	}
	return nil
}

func runInstall(args []string) error {
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

	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Minute)
	defer cancel()

	manifest, err := releases.Fetch(ctx, http.DefaultClient, cfg.ReleaseManifestURL)
	if err != nil {
		return err
	}
	if err := checkManifestTitle(cfg, manifest); err != nil {
		return err
	}
	zipPath, err := releases.DownloadZip(ctx, http.DefaultClient, manifest.ZipURL, *outDir)
	if err != nil {
		return err
	}
	if err := checksum.VerifyFileSHA256(zipPath, manifest.SHA256); err != nil {
		return err
	}

	installer := roku.HTTPInstaller{}
	err = installer.Install(ctx, roku.Target{
		IP:       *ip,
		Username: cfg.DefaultUsername,
		Password: *password,
	}, zipPath)
	if err != nil {
		return err
	}
	fmt.Printf("Install complete: %s %s\n", cfg.AppName, manifest.Version)
	fmt.Println("The beta replaced any previous sideloaded channel on this Roku.")
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

var errUsage = errors.New("usage: roku-beta-loader <config|release|roku|install>")

func usage() error {
	fmt.Println(`Usage:
  roku-beta-loader config validate --config PATH
  roku-beta-loader release check --config PATH
  roku-beta-loader roku discover
  roku-beta-loader install --config PATH --ip ROKU_IP --password PASSWORD`)
	return nil
}
