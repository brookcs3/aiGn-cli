package main

import (
	"fmt"
	"io"
	"log"
	"os"

	"github.com/charmbracelet/glamour"
	"github.com/charmbracelet/glamour/styles"
	"github.com/muesli/termenv"
)

func main() {
	var content []byte
	var err error

	if len(os.Args) < 2 {
		// Try reading from stdin
		stat, _ := os.Stdin.Stat()
		if (stat.Mode() & os.ModeCharDevice) == 0 {
			content, err = io.ReadAll(os.Stdin)
			if err != nil {
				log.Fatalf("Error reading from stdin: %v", err)
			}
		} else {
			fmt.Println("Usage: go run main.go <markdown-file> or pipe markdown to stdin")
			os.Exit(1)
		}
	} else {
		filePath := os.Args[1]
		content, err = os.ReadFile(filePath)
		if err != nil {
			log.Fatalf("Error reading file: %v", err)
		}
	}

	// Create a custom style based on the dark theme but without prefixes
	style := styles.DarkStyleConfig
	style.H1.Prefix = ""
	style.H1.Suffix = ""
	style.H2.Prefix = ""
	style.H2.Suffix = ""

	// Create a new renderer with the specific content style
	r, err := glamour.NewTermRenderer(
		glamour.WithStyles(style),
		glamour.WithWordWrap(80),
		glamour.WithColorProfile(termenv.TrueColor),
	)
	if err != nil {
		log.Fatalf("Error initializing renderer: %v", err)
	}

	out, err := r.Render(string(content))
	if err != nil {
		log.Fatalf("Error rendering markdown: %v", err)
	}

	fmt.Print(out)
}
