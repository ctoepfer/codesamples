package config

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestGoSourceHasNoAppSpecificBranding(t *testing.T) {
	root := filepath.Join("..", "..")
	banned := []string{"Io" + "kom", "io" + "kom.com", "Io" + "kom Signage"}

	err := filepath.WalkDir(root, func(path string, entry os.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if entry.IsDir() {
			return nil
		}
		if filepath.Ext(path) != ".go" {
			return nil
		}
		data, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		text := string(data)
		for _, value := range banned {
			if strings.Contains(text, value) {
				t.Fatalf("%s contains app-specific string %q", path, value)
			}
		}
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
}
