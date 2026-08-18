package discovery

import (
	"bufio"
	"context"
	"encoding/xml"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"
)

const (
	ssdpAddr     = "239.255.255.250:1900"
	rokuSearchST = "roku:ecp"
	ecpPort      = "8060"

	// ssdpWindow is how long to listen for SSDP responses after the last M-SEARCH.
	// MX in the request is set to 2, so devices may respond any time within that
	// window; we add a 1 second buffer.
	ssdpWindow = 3 * time.Second

	// probeTimeout is the per-host timeout for the subnet-scan fallback.
	probeTimeout = 600 * time.Millisecond
)

// Device is a discovered Roku device.
type Device struct {
	Name      string // friendly name from /query/device-info, e.g. "Living Room Roku"
	ModelName string // model name, e.g. "Roku Ultra"
	IP        string
	Location  string // base ECP URL, e.g. "http://192.168.1.50:8060/"
	USN       string
	Serial    string
}

// Discover finds Roku devices on the local network.
//
// It first tries SSDP multicast (M-SEARCH). If that returns nothing — which
// happens when multicast is filtered by a router, VPN, or guest Wi-Fi — it
// falls back to scanning every host on each local /24 subnet for port 8060.
//
// Both phases enrich results with the Roku's user-device-name and model via
// the ECP /query/device-info endpoint.
func Discover(ctx context.Context) ([]Device, error) {
	// Phase 1: SSDP multicast. Give it ssdpWindow, leaving time for the fallback.
	ssdpCtx, ssdpCancel := context.WithTimeout(ctx, ssdpWindow)
	defer ssdpCancel()

	ssdpDevices, ssdpErr := ssdpDiscover(ssdpCtx)
	if len(ssdpDevices) > 0 {
		return enrichAll(ctx, ssdpDevices), nil
	}

	// Phase 2: subnet probe. Run this even if SSDP errored, as long as the
	// parent context still has time.
	if ctx.Err() != nil {
		if ssdpErr != nil {
			return nil, ssdpErr
		}
		return nil, nil
	}
	return subnetScan(ctx)
}

// ssdpDiscover sends M-SEARCH and collects responses until the context deadline.
func ssdpDiscover(ctx context.Context) ([]Device, error) {
	addr, err := net.ResolveUDPAddr("udp4", ssdpAddr)
	if err != nil {
		return nil, fmt.Errorf("resolve SSDP address: %w", err)
	}
	conn, err := net.ListenPacket("udp4", ":0")
	if err != nil {
		return nil, fmt.Errorf("start Roku discovery: %w", err)
	}
	defer conn.Close()

	// MX: 2 → devices may respond within 2 s; we listen for 3 s total.
	msg := strings.Join([]string{
		"M-SEARCH * HTTP/1.1",
		"HOST: 239.255.255.250:1900",
		`MAN: "ssdp:discover"`,
		"MX: 2",
		"ST: " + rokuSearchST,
		"",
		"",
	}, "\r\n")

	// Send the request twice to improve reliability (packet loss, missed wake).
	for i := 0; i < 2; i++ {
		if _, err := conn.WriteTo([]byte(msg), addr); err != nil {
			return nil, fmt.Errorf("send Roku discovery request: %w", err)
		}
		time.Sleep(150 * time.Millisecond)
	}

	deadline, ok := ctx.Deadline()
	if !ok {
		deadline = time.Now().Add(ssdpWindow)
	}
	if err := conn.SetReadDeadline(deadline); err != nil {
		return nil, fmt.Errorf("set discovery deadline: %w", err)
	}

	seen := map[string]Device{}
	buf := make([]byte, 8192)
	for {
		n, _, err := conn.ReadFrom(buf)
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
			seen[device.Location] = device
		}
	}

	devices := make([]Device, 0, len(seen))
	for _, d := range seen {
		devices = append(devices, d)
	}
	return devices, nil
}

// enrichAll calls EnrichDevice concurrently for every device in the slice.
func enrichAll(ctx context.Context, devices []Device) []Device {
	enrichCtx, cancel := context.WithTimeout(ctx, 2*time.Second)
	defer cancel()
	out := make([]Device, len(devices))
	var wg sync.WaitGroup
	for i, d := range devices {
		wg.Add(1)
		go func(idx int, dev Device) {
			defer wg.Done()
			out[idx] = EnrichDevice(enrichCtx, nil, dev)
		}(i, d)
	}
	wg.Wait()
	return out
}

// subnetScan probes every address on each local /24 subnet for port 8060.
// This is the fallback when SSDP multicast is unavailable.
func subnetScan(ctx context.Context) ([]Device, error) {
	localIPs, err := localIPv4Addrs()
	if err != nil || len(localIPs) == 0 {
		return nil, nil
	}

	// Build candidate list — all /24 peers, deduped.
	candidates := map[string]struct{}{}
	for _, local := range localIPs {
		base := local.Mask(net.CIDRMask(24, 32))
		for i := 1; i < 255; i++ {
			candidate := net.IP{base[0], base[1], base[2], byte(i)}.String()
			if candidate != local.String() {
				candidates[candidate] = struct{}{}
			}
		}
	}

	results := make(chan Device, len(candidates))
	var wg sync.WaitGroup
	for ip := range candidates {
		wg.Add(1)
		go func(host string) {
			defer wg.Done()
			if d, ok := probeECP(ctx, host); ok {
				results <- d
			}
		}(ip)
	}
	go func() {
		wg.Wait()
		close(results)
	}()

	var devices []Device
	for d := range results {
		devices = append(devices, d)
	}
	return devices, nil
}

// probeECP tries to fetch /query/device-info from the given IP on port 8060.
func probeECP(ctx context.Context, ip string) (Device, bool) {
	probeCtx, cancel := context.WithTimeout(ctx, probeTimeout)
	defer cancel()

	ecpURL := "http://" + net.JoinHostPort(ip, ecpPort) + "/query/device-info"
	req, err := http.NewRequestWithContext(probeCtx, http.MethodGet, ecpURL, nil)
	if err != nil {
		return Device{}, false
	}
	resp, err := (&http.Client{}).Do(req)
	if err != nil {
		return Device{}, false
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return Device{}, false
	}
	body, err := io.ReadAll(io.LimitReader(resp.Body, 64<<10))
	if err != nil {
		return Device{}, false
	}

	name, model, serial := parseDeviceInfo(body)
	if name == "" && model == "" {
		// Responded on port 8060 but no device-info — treat as anonymous Roku.
		name = "Roku (" + ip + ")"
	}
	return Device{
		IP:        ip,
		Name:      displayName(name, model, ip),
		ModelName: model,
		Serial:    serial,
		Location:  "http://" + net.JoinHostPort(ip, ecpPort) + "/",
	}, true
}

// ParseSSDPResponse parses a single SSDP UDP response packet into a Device.
// The device is not yet enriched with ECP device-info.
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

// EnrichDevice fetches /query/device-info from the Roku's ECP endpoint and
// populates the device's Name, ModelName, and Serial fields.
func EnrichDevice(ctx context.Context, client *http.Client, device Device) Device {
	if client == nil {
		client = &http.Client{Timeout: 2 * time.Second}
	}
	ecpURL := strings.TrimRight(device.Location, "/") + "/query/device-info"
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, ecpURL, nil)
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
	body, err := io.ReadAll(io.LimitReader(resp.Body, 64<<10))
	if err != nil {
		return device
	}

	name, model, serial := parseDeviceInfo(body)
	device.Name = displayName(name, model, device.IP)
	if model != "" {
		device.ModelName = model
	}
	if serial != "" {
		device.Serial = serial
	}
	return device
}

// deviceInfoXML mirrors the relevant fields of Roku's /query/device-info response.
type deviceInfoXML struct {
	XMLName        xml.Name `xml:"device-info"`
	UserDeviceName string   `xml:"user-device-name"`
	ModelName      string   `xml:"model-name"`
	ModelNumber    string   `xml:"model-number"`
	SerialNumber   string   `xml:"serial-number"`
}

// parseDeviceInfo extracts the user-assigned name, model name, and serial from
// the XML body returned by /query/device-info.
func parseDeviceInfo(body []byte) (name, model, serial string) {
	var info deviceInfoXML
	if err := xml.Unmarshal(body, &info); err != nil {
		return "", "", ""
	}
	name = strings.TrimSpace(info.UserDeviceName)
	model = strings.TrimSpace(info.ModelName)
	if model == "" {
		model = strings.TrimSpace(info.ModelNumber)
	}
	serial = strings.TrimSpace(info.SerialNumber)
	return name, model, serial
}

// displayName builds a human-readable device name from the ECP data.
// Priority: user-assigned name > model name > fallback with IP.
func displayName(userName, modelName, ip string) string {
	if userName != "" && modelName != "" {
		return userName + " (" + modelName + ")"
	}
	if userName != "" {
		return userName
	}
	if modelName != "" {
		return modelName + " (" + ip + ")"
	}
	return "Roku (" + ip + ")"
}

// localIPv4Addrs returns all non-loopback IPv4 addresses on the machine.
func localIPv4Addrs() ([]net.IP, error) {
	ifaces, err := net.InterfaceAddrs()
	if err != nil {
		return nil, err
	}
	var addrs []net.IP
	for _, iface := range ifaces {
		ipNet, ok := iface.(*net.IPNet)
		if !ok {
			continue
		}
		v4 := ipNet.IP.To4()
		if v4 == nil || v4.IsLoopback() {
			continue
		}
		addrs = append(addrs, v4)
	}
	return addrs, nil
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
