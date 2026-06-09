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
