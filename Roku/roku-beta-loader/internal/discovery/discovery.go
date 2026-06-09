package discovery

import (
	"bufio"
	"context"
	"errors"
	"fmt"
	"net"
	"net/http"
	"net/url"
	"strings"
	"time"
)

const (
	ssdpAddr       = "239.255.255.250:1900"
	rokuSearchST   = "roku:ecp"
	defaultWaitTime = 3 * time.Second
)

type Device struct {
	Name     string
	IP       string
	Location string
	USN      string
	Serial   string
}

func Discover(ctx context.Context) ([]Device, error) {
	addr, err := net.ResolveUDPAddr("udp4", ssdpAddr)
	if err != nil {
		return nil, fmt.Errorf("resolve SSDP address: %w", err)
	}
	conn, err := net.ListenPacket("udp4", ":0")
	if err != nil {
		return nil, fmt.Errorf("start Roku discovery: %w", err)
	}
	defer conn.Close()

	msg := strings.Join([]string{
		"M-SEARCH * HTTP/1.1",
		"HOST: 239.255.255.250:1900",
		`MAN: "ssdp:discover"`,
		"MX: 3",
		"ST: " + rokuSearchST,
		"",
		"",
	}, "\r\n")
	if _, err := conn.WriteTo([]byte(msg), addr); err != nil {
		return nil, fmt.Errorf("send Roku discovery request: %w", err)
	}

	deadline, ok := ctx.Deadline()
	if !ok {
		deadline = time.Now().Add(defaultWaitTime)
	}
	if err := conn.SetReadDeadline(deadline); err != nil {
		return nil, fmt.Errorf("set discovery deadline: %w", err)
	}

	seen := map[string]Device{}
	buf := make([]byte, 8192)
	for {
		n, err := conn.Read(buf)
		if err != nil {
			var netErr net.Error
			if errors.As(err, &netErr) && netErr.Timeout() {
				break
			}
			if ctx.Err() != nil {
				break
			}
			return nil, fmt.Errorf("read Roku discovery response: %w", err)
		}
		device, err := ParseSSDPResponse(string(buf[:n]))
		if err == nil && device.Location != "" {
			key := device.Location
			if key == "" {
				key = device.IP
			}
			seen[key] = device
		}
	}

	devices := make([]Device, 0, len(seen))
	for _, device := range seen {
		devices = append(devices, device)
	}
	return devices, nil
}

func ParseSSDPResponse(raw string) (Device, error) {
	headers := map[string]string{}
	scanner := bufio.NewScanner(strings.NewReader(raw))
	if !scanner.Scan() {
		return Device{}, errors.New("empty SSDP response")
	}
	status := scanner.Text()
	if !strings.Contains(status, "200") {
		return Device{}, fmt.Errorf("unexpected SSDP response status: %s", status)
	}
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			break
		}
		key, value, ok := strings.Cut(line, ":")
		if !ok {
			continue
		}
		headers[strings.ToLower(strings.TrimSpace(key))] = strings.TrimSpace(value)
	}

	st := strings.ToLower(headers["st"])
	if st != "" && !strings.Contains(st, "roku:ecp") {
		return Device{}, fmt.Errorf("not a Roku ECP response: %s", headers["st"])
	}

	location := headers["location"]
	parsed, err := url.Parse(location)
	if err != nil || parsed.Hostname() == "" {
		return Device{}, fmt.Errorf("SSDP response missing valid LOCATION")
	}

	return Device{
		Name:     "Roku",
		IP:       parsed.Hostname(),
		Location: location,
		USN:      headers["usn"],
		Serial:   serialFromUSN(headers["usn"]),
	}, nil
}

func EnrichDevice(ctx context.Context, client *http.Client, device Device) Device {
	if client == nil {
		client = &http.Client{Timeout: 2 * time.Second}
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, strings.TrimRight(device.Location, "/")+"/query/device-info", nil)
	if err != nil {
		return device
	}
	resp, err := client.Do(req)
	if err != nil {
		return device
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode > 299 {
		return device
	}
	device.Name = "Roku (" + device.IP + ")"
	return device
}

func serialFromUSN(usn string) string {
	parts := strings.Split(usn, ":")
	if len(parts) == 0 {
		return ""
	}
	last := parts[len(parts)-1]
	last = strings.TrimPrefix(last, "roku")
	return strings.Trim(last, "- ")
}
