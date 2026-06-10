package roku

import (
	"bytes"
	"context"
	"crypto/md5"
	"crypto/rand"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"mime/multipart"
	"net"
	"net/http"
	"net/textproto"
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

type InstallerOptions struct {
	Port           string
	Path           string
	SubmitField    string
	SubmitValue    string
	ArchiveField   string
	UploadFilename string
}

func DefaultInstallerOptions() InstallerOptions {
	return InstallerOptions{
		Port:           "80",
		Path:           "/plugin_install",
		SubmitField:    "mysubmit",
		SubmitValue:    "Install",
		ArchiveField:   "archive",
		UploadFilename: "channel.zip",
	}
}

type HTTPInstaller struct {
	Client  *http.Client
	Options InstallerOptions
}

func (i HTTPInstaller) Install(ctx context.Context, target Target, zipPath string) error {
	if strings.TrimSpace(target.IP) == "" {
		return errors.New("Roku IP address is required")
	}
	if strings.TrimSpace(target.Username) == "" {
		return errors.New("Roku developer username is required")
	}
	if target.Password == "" {
		return errors.New("Roku developer password is required and is not stored by this tool")
	}

	client := i.Client
	if client == nil {
		client = &http.Client{Timeout: 2 * time.Minute}
	}
	options := i.Options.withDefaults()

	var body bytes.Buffer
	writer := multipart.NewWriter(&body)
	if err := writer.WriteField(options.SubmitField, options.SubmitValue); err != nil {
		return fmt.Errorf("prepare install request: %w", err)
	}
	partHeader := textproto.MIMEHeader{}
	partHeader.Set("Content-Disposition", fmt.Sprintf(`form-data; name=%q; filename=%q`, options.ArchiveField, options.UploadFilename))
	partHeader.Set("Content-Type", "application/zip")
	part, err := writer.CreatePart(partHeader)
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

	installURL := "http://" + net.JoinHostPort(target.IP, options.Port) + options.Path
	contentType := writer.FormDataContentType()

	// Roku's developer web server authenticates with HTTP Digest, not Basic.
	// Probe with a credential-free request to obtain the digest challenge, then
	// replay the upload with a computed Authorization header.
	challenge, err := i.digestChallenge(ctx, client, installURL)
	if err != nil {
		return err
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, installURL, bytes.NewReader(body.Bytes()))
	if err != nil {
		return fmt.Errorf("create install request: %w", err)
	}
	req.Header.Set("Content-Type", contentType)
	if challenge != "" {
		auth, err := digestAuthorization(challenge, http.MethodPost, options.Path, target.Username, target.Password)
		if err != nil {
			return err
		}
		req.Header.Set("Authorization", auth)
	}

	resp, err := client.Do(req)
	if err != nil {
		return FriendlyInstallError(err)
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(io.LimitReader(resp.Body, 1<<20))

	if resp.StatusCode == http.StatusUnauthorized || resp.StatusCode == http.StatusForbidden {
		return errors.New("Roku rejected the developer credentials. Check the username, developer password, and Developer Mode setup")
	}
	if resp.StatusCode == http.StatusNotFound {
		return errors.New("Roku developer installer was not found. Confirm Developer Mode is enabled and the Roku has restarted")
	}
	// Roku reports the real outcome in the response body regardless of whether the
	// status is 200 or 4xx, so inspect it before falling back to the status code.
	if failure := extractInstallFailure(respBody); failure != "" {
		return fmt.Errorf("Roku rejected the channel zip: %s", failure)
	}
	if installSucceeded(respBody) {
		return nil
	}
	if resp.StatusCode < 200 || resp.StatusCode > 299 {
		return fmt.Errorf("Roku install failed: device returned %s", resp.Status)
	}
	return nil
}

// digestChallenge sends a credential-free request and returns the value of the
// WWW-Authenticate header from the expected 401 response. An empty string means
// the server did not request authentication.
func (i HTTPInstaller) digestChallenge(ctx context.Context, client *http.Client, installURL string) (string, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, installURL, nil)
	if err != nil {
		return "", fmt.Errorf("create auth probe request: %w", err)
	}
	resp, err := client.Do(req)
	if err != nil {
		return "", FriendlyInstallError(err)
	}
	defer resp.Body.Close()
	io.Copy(io.Discard, io.LimitReader(resp.Body, 1<<16))
	if resp.StatusCode != http.StatusUnauthorized {
		return "", nil
	}
	return resp.Header.Get("WWW-Authenticate"), nil
}

// digestAuthorization builds an RFC 2617 Digest Authorization header value for
// the given challenge, using qop="auth" and MD5 (Roku's developer server).
func digestAuthorization(challenge, method, uri, username, password string) (string, error) {
	params := parseDigestChallenge(challenge)
	realm := params["realm"]
	nonce := params["nonce"]
	if realm == "" || nonce == "" {
		return "", fmt.Errorf("unsupported Roku auth challenge: %q", challenge)
	}
	qop := selectQOP(params["qop"])

	cnonce, err := randomHex(8)
	if err != nil {
		return "", err
	}
	const nc = "00000001"

	ha1 := md5Hex(username + ":" + realm + ":" + password)
	ha2 := md5Hex(method + ":" + uri)

	var response string
	if qop == "auth" {
		response = md5Hex(strings.Join([]string{ha1, nonce, nc, cnonce, qop, ha2}, ":"))
	} else {
		response = md5Hex(strings.Join([]string{ha1, nonce, ha2}, ":"))
	}

	parts := []string{
		fmt.Sprintf("username=%q", username),
		fmt.Sprintf("realm=%q", realm),
		fmt.Sprintf("nonce=%q", nonce),
		fmt.Sprintf("uri=%q", uri),
		fmt.Sprintf("response=%q", response),
	}
	if qop == "auth" {
		parts = append(parts, "qop=auth", "nc="+nc, fmt.Sprintf("cnonce=%q", cnonce))
	}
	if opaque := params["opaque"]; opaque != "" {
		parts = append(parts, fmt.Sprintf("opaque=%q", opaque))
	}
	if algorithm := params["algorithm"]; algorithm != "" {
		parts = append(parts, "algorithm="+algorithm)
	}
	return "Digest " + strings.Join(parts, ", "), nil
}

func parseDigestChallenge(challenge string) map[string]string {
	params := map[string]string{}
	challenge = strings.TrimSpace(strings.TrimPrefix(strings.TrimSpace(challenge), "Digest"))
	for _, field := range splitDigestFields(challenge) {
		key, value, ok := strings.Cut(field, "=")
		if !ok {
			continue
		}
		key = strings.TrimSpace(key)
		value = strings.Trim(strings.TrimSpace(value), `"`)
		params[strings.ToLower(key)] = value
	}
	return params
}

// splitDigestFields splits on commas that are not inside quoted values.
func splitDigestFields(s string) []string {
	var fields []string
	var current strings.Builder
	inQuotes := false
	for _, r := range s {
		switch {
		case r == '"':
			inQuotes = !inQuotes
			current.WriteRune(r)
		case r == ',' && !inQuotes:
			fields = append(fields, current.String())
			current.Reset()
		default:
			current.WriteRune(r)
		}
	}
	if strings.TrimSpace(current.String()) != "" {
		fields = append(fields, current.String())
	}
	return fields
}

func selectQOP(qop string) string {
	for _, candidate := range strings.Split(qop, ",") {
		if strings.TrimSpace(candidate) == "auth" {
			return "auth"
		}
	}
	return ""
}

func md5Hex(s string) string {
	sum := md5.Sum([]byte(s))
	return hex.EncodeToString(sum[:])
}

func randomHex(n int) (string, error) {
	buf := make([]byte, n)
	if _, err := rand.Read(buf); err != nil {
		return "", fmt.Errorf("generate client nonce: %w", err)
	}
	return hex.EncodeToString(buf), nil
}

func extractInstallFailure(body []byte) string {
	text := string(body)
	const marker = "Install Failure:"
	idx := strings.Index(text, marker)
	if idx == -1 {
		return ""
	}
	rest := text[idx+len(marker):]
	if end := strings.IndexAny(rest, "'\"<"); end != -1 {
		rest = rest[:end]
	}
	return strings.TrimSpace(rest)
}

func installSucceeded(body []byte) bool {
	text := string(body)
	return strings.Contains(text, "Install Success") ||
		strings.Contains(text, "Identical to previous version")
}

func (o InstallerOptions) withDefaults() InstallerOptions {
	defaults := DefaultInstallerOptions()
	if o.Port == "" {
		o.Port = defaults.Port
	}
	if o.Path == "" {
		o.Path = defaults.Path
	}
	if o.SubmitField == "" {
		o.SubmitField = defaults.SubmitField
	}
	if o.SubmitValue == "" {
		o.SubmitValue = defaults.SubmitValue
	}
	if o.ArchiveField == "" {
		o.ArchiveField = defaults.ArchiveField
	}
	if o.UploadFilename == "" {
		o.UploadFilename = defaults.UploadFilename
	}
	return o
}

func FriendlyInstallError(err error) error {
	var netErr net.Error
	if errors.As(err, &netErr) && netErr.Timeout() {
		return fmt.Errorf("could not reach Roku before timeout. Check that the Roku is on the same network and Developer Mode is enabled: %w", err)
	}
	return fmt.Errorf("could not upload to Roku. Check the IP address, local network, VPN/firewall settings, and Developer Mode: %w", err)
}
