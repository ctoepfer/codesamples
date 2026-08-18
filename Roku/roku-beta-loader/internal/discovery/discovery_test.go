package discovery

import "testing"

func TestParseSSDPResponse(t *testing.T) {
	raw := "HTTP/1.1 200 OK\r\n" +
		"ST: roku:ecp\r\n" +
		"USN: uuid:roku:ecp:ABC123\r\n" +
		"LOCATION: http://192.168.1.25:8060/\r\n" +
		"CACHE-CONTROL: max-age=3600\r\n\r\n"

	device, err := ParseSSDPResponse(raw)
	if err != nil {
		t.Fatalf("ParseSSDPResponse returned error: %v", err)
	}
	if device.IP != "192.168.1.25" {
		t.Fatalf("unexpected IP: %q", device.IP)
	}
	if device.Serial != "ABC123" {
		t.Fatalf("unexpected serial: %q", device.Serial)
	}
}

func TestParseSSDPResponseRejectsNonRoku(t *testing.T) {
	raw := "HTTP/1.1 200 OK\r\n" +
		"ST: urn:schemas-upnp-org:device:MediaServer:1\r\n" +
		"LOCATION: http://192.168.1.50:8000/\r\n\r\n"

	if _, err := ParseSSDPResponse(raw); err == nil {
		t.Fatal("expected non-Roku response to be rejected")
	}
}

func TestParseDeviceInfo(t *testing.T) {
	body := []byte(`<?xml version="1.0" encoding="UTF-8" ?>
<device-info>
  <udn>12345678-abcd-1234-abcd-123456789abc</udn>
  <serial-number>X00000AAAAAA</serial-number>
  <vendor-name>Roku</vendor-name>
  <model-number>4800X</model-number>
  <model-name>Roku Ultra</model-name>
  <user-device-name>Living Room Roku</user-device-name>
  <software-version>13.0.0</software-version>
</device-info>`)

	name, model, serial := parseDeviceInfo(body)
	if name != "Living Room Roku" {
		t.Fatalf("unexpected name: %q", name)
	}
	if model != "Roku Ultra" {
		t.Fatalf("unexpected model: %q", model)
	}
	if serial != "X00000AAAAAA" {
		t.Fatalf("unexpected serial: %q", serial)
	}
}

func TestParseDeviceInfoFallsBackToModelNumber(t *testing.T) {
	body := []byte(`<device-info>
  <serial-number>SN123</serial-number>
  <model-number>3941X</model-number>
</device-info>`)

	_, model, serial := parseDeviceInfo(body)
	if model != "3941X" {
		t.Fatalf("expected model-number fallback, got %q", model)
	}
	if serial != "SN123" {
		t.Fatalf("unexpected serial: %q", serial)
	}
}

func TestParseDeviceInfoInvalidXML(t *testing.T) {
	name, model, serial := parseDeviceInfo([]byte("not xml"))
	if name != "" || model != "" || serial != "" {
		t.Fatalf("expected empty results for invalid XML, got name=%q model=%q serial=%q", name, model, serial)
	}
}

func TestDisplayName(t *testing.T) {
	cases := []struct {
		userName, modelName, ip, want string
	}{
		{"Living Room", "Roku Ultra", "192.168.1.5", "Living Room (Roku Ultra)"},
		{"Living Room", "", "192.168.1.5", "Living Room"},
		{"", "Roku Ultra", "192.168.1.5", "Roku Ultra (192.168.1.5)"},
		{"", "", "192.168.1.5", "Roku (192.168.1.5)"},
	}
	for _, c := range cases {
		got := displayName(c.userName, c.modelName, c.ip)
		if got != c.want {
			t.Errorf("displayName(%q, %q, %q) = %q, want %q", c.userName, c.modelName, c.ip, got, c.want)
		}
	}
}

func TestLocalIPv4Addrs(t *testing.T) {
	addrs, err := localIPv4Addrs()
	if err != nil {
		t.Fatalf("localIPv4Addrs returned error: %v", err)
	}
	for _, addr := range addrs {
		if addr.IsLoopback() {
			t.Errorf("localIPv4Addrs returned loopback address: %v", addr)
		}
		if addr.To4() == nil {
			t.Errorf("localIPv4Addrs returned non-IPv4 address: %v", addr)
		}
	}
}
