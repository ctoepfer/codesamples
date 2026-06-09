package roku

import (
	"context"
	"strings"
	"testing"
)

func TestInstallRequiresUsername(t *testing.T) {
	installer := HTTPInstaller{}
	err := installer.Install(context.Background(), Target{
		IP:       "192.168.1.123",
		Password: "secret",
	}, "channel.zip")
	if err == nil || !strings.Contains(err.Error(), "username is required") {
		t.Fatalf("expected username validation error, got %v", err)
	}
}

func TestDefaultInstallerOptions(t *testing.T) {
	options := DefaultInstallerOptions()
	if options.Port != "80" ||
		options.Path != "/plugin_install" ||
		options.SubmitField != "mysubmit" ||
		options.SubmitValue != "Install" ||
		options.ArchiveField != "archive" ||
		options.UploadFilename != "channel.zip" {
		t.Fatalf("unexpected default installer options: %+v", options)
	}
}
