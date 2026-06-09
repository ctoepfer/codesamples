package roku

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"io"
	"mime/multipart"
	"net"
	"net/http"
	"os"
	"strings"
	"time"
)

type Installer interface {
	Install(ctx context.Context, target Target, zipPath string) error
}

type Target struct {
	IP       string
	Username string
	Password string
}

type HTTPInstaller struct {
	Client *http.Client
}

func (i HTTPInstaller) Install(ctx context.Context, target Target, zipPath string) error {
	if strings.TrimSpace(target.IP) == "" {
		return errors.New("Roku IP address is required")
	}
	if strings.TrimSpace(target.Username) == "" {
		target.Username = "rokudev"
	}
	if target.Password == "" {
		return errors.New("Roku developer password is required and is not stored by this tool")
	}

	client := i.Client
	if client == nil {
		client = &http.Client{Timeout: 2 * time.Minute}
	}

	var body bytes.Buffer
	writer := multipart.NewWriter(&body)
	if err := writer.WriteField("mysubmit", "Install"); err != nil {
		return fmt.Errorf("prepare install request: %w", err)
	}
	part, err := writer.CreateFormFile("archive", "channel.zip")
	if err != nil {
		return fmt.Errorf("prepare zip upload: %w", err)
	}
	file, err := os.Open(zipPath)
	if err != nil {
		return fmt.Errorf("open verified zip for upload: %w", err)
	}
	if _, err := io.Copy(part, file); err != nil {
		file.Close()
		return fmt.Errorf("read verified zip for upload: %w", err)
	}
	if err := file.Close(); err != nil {
		return fmt.Errorf("close verified zip: %w", err)
	}
	if err := writer.Close(); err != nil {
		return fmt.Errorf("finalize install request: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, "http://"+net.JoinHostPort(target.IP, "80")+"/plugin_install", &body)
	if err != nil {
		return fmt.Errorf("create install request: %w", err)
	}
	req.SetBasicAuth(target.Username, target.Password)
	req.Header.Set("Content-Type", writer.FormDataContentType())

	resp, err := client.Do(req)
	if err != nil {
		return FriendlyInstallError(err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusUnauthorized || resp.StatusCode == http.StatusForbidden {
		return errors.New("Roku rejected the developer credentials. Check the username, developer password, and Developer Mode setup")
	}
	if resp.StatusCode == http.StatusNotFound {
		return errors.New("Roku developer installer was not found. Confirm Developer Mode is enabled and the Roku has restarted")
	}
	if resp.StatusCode < 200 || resp.StatusCode > 299 {
		return fmt.Errorf("Roku install failed: device returned %s", resp.Status)
	}
	return nil
}

func FriendlyInstallError(err error) error {
	var netErr net.Error
	if errors.As(err, &netErr) && netErr.Timeout() {
		return fmt.Errorf("could not reach Roku before timeout. Check that the Roku is on the same network and Developer Mode is enabled: %w", err)
	}
	return fmt.Errorf("could not upload to Roku. Check the IP address, local network, VPN/firewall settings, and Developer Mode: %w", err)
}
