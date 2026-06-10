//go:build wails

package main

import (
	"embed"

	"github.com/ctoepfer/codesamples/Roku/roku-beta-loader/internal/appflow"
	"github.com/ctoepfer/codesamples/Roku/roku-beta-loader/internal/gui"
	"github.com/wailsapp/wails/v2"
	"github.com/wailsapp/wails/v2/pkg/options"
	"github.com/wailsapp/wails/v2/pkg/options/assetserver"
)

//go:embed all:frontend
var assets embed.FS

func main() {
	svc := appflow.New()
	app := gui.NewApp(svc)

	err := wails.Run(&options.App{
		Title:            "Roku Beta Loader",
		Width:            500,
		Height:           720,
		MinWidth:         400,
		MinHeight:        600,
		BackgroundColour: &options.RGBA{R: 248, G: 248, B: 250, A: 1},
		AssetServer: &assetserver.Options{
			Assets: assets,
		},
		OnStartup: app.Startup,
		Bind:      []interface{}{app},
	})
	if err != nil {
		println("Error:", err.Error())
	}
}
