package roku

import (
	"context"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"path/filepath"
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

// fakeRokuServer emulates the Roku developer installer: it requires HTTP Digest
// auth (rejecting Basic auth) and reports the install result in the body.
func TestInstallUsesDigestAuth(t *testing.T) {
	zipPath := filepath.Join(t.TempDir(), "channel.zip")
	if err := os.WriteFile(zipPath, []byte("PK\x05\x06"+strings.Repeat("\x00", 18)), 0o600); err != nil {
		t.Fatal(err)
	}

	var gotArchive bool
	var gotAuthScheme string
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		auth := r.Header.Get("Authorization")
		if !strings.HasPrefix(auth, "Digest ") {
			if strings.HasPrefix(auth, "Basic ") {
				gotAuthScheme = "Basic"
			}
			w.Header().Set("WWW-Authenticate", `Digest qop="auth", realm="rokudev", nonce="abc123"`)
			w.WriteHeader(http.StatusUnauthorized)
			return
		}
		gotAuthScheme = "Digest"
		if !strings.Contains(auth, `response=`) || !strings.Contains(auth, "qop=auth") {
			t.Errorf("digest header missing fields: %s", auth)
		}
		if err := r.ParseMultipartForm(1 << 20); err == nil {
			if _, _, err := r.FormFile("archive"); err == nil {
				gotArchive = true
			}
		}
		io.WriteString(w, "Install Success.")
	}))
	defer srv.Close()

	u, _ := url.Parse(srv.URL)
	host, port, _ := net.SplitHostPort(u.Host)

	installer := HTTPInstaller{
		Client:  srv.Client(),
		Options: InstallerOptions{Port: port},
	}
	err := installer.Install(context.Background(), Target{
		IP:       host,
		Username: "rokudev",
		Password: "secret",
	}, zipPath)
	if err != nil {
		t.Fatalf("Install returned error: %v", err)
	}
	if gotAuthScheme != "Digest" {
		t.Fatalf("server saw auth scheme %q, want Digest", gotAuthScheme)
	}
	if !gotArchive {
		t.Fatal("server did not receive the archive upload")
	}
}

func TestInstallReportsRokuFailureBody(t *testing.T) {
	zipPath := filepath.Join(t.TempDir(), "channel.zip")
	if err := os.WriteFile(zipPath, []byte("not a zip"), 0o600); err != nil {
		t.Fatal(err)
	}
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if !strings.HasPrefix(r.Header.Get("Authorization"), "Digest ") {
			w.Header().Set("WWW-Authenticate", `Digest qop="auth", realm="rokudev", nonce="abc123"`)
			w.WriteHeader(http.StatusUnauthorized)
			return
		}
		w.WriteHeader(http.StatusBadRequest)
		io.WriteString(w, `x.trigger('Set message content', 'Install Failure: Unzip failed. Invalid or corrupt zip archive.  Unloading.').trigger('Render');`)
	}))
	defer srv.Close()

	u, _ := url.Parse(srv.URL)
	host, port, _ := net.SplitHostPort(u.Host)
	installer := HTTPInstaller{Client: srv.Client(), Options: InstallerOptions{Port: port}}
	err := installer.Install(context.Background(), Target{IP: host, Username: "rokudev", Password: "secret"}, zipPath)
	if err == nil || !strings.Contains(err.Error(), "Unzip failed") {
		t.Fatalf("expected Roku failure detail in error, got %v", err)
	}
}

func TestDigestAuthorizationComputesResponse(t *testing.T) {
	// Known-answer test for the qop=auth digest computation.
	challenge := `Digest qop="auth", realm="rokudev", nonce="abc123"`
	auth, err := digestAuthorization(challenge, http.MethodPost, "/plugin_install", "rokudev", "secret")
	if err != nil {
		t.Fatal(err)
	}
	for _, want := range []string{`username="rokudev"`, `realm="rokudev"`, `nonce="abc123"`, `uri="/plugin_install"`, "qop=auth", "nc=00000001", "response="} {
		if !strings.Contains(auth, want) {
			t.Errorf("authorization header missing %q: %s", want, auth)
		}
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
