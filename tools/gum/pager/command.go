package pager

import (
	"fmt"
	"regexp"

	"github.com/charmbracelet/bubbles/help"
	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/gum/internal/stdin"
	"github.com/charmbracelet/gum/internal/timeout"
)

// Run provides a shell script interface for the viewport bubble.
// https://github.com/charmbracelet/bubbles/viewport
func (o Options) Run() error {
	vp := viewport.New(o.Style.Width, o.Style.Height)
	vp.Style = o.Style.ToLipgloss()

	if o.Content == "" {
		stdin, err := stdin.Read()
		if err != nil {
			return fmt.Errorf("unable to read stdin")
		}
		if stdin != "" {
			// Sanitize the input from stdin by removing backspace sequences.
			backspace := regexp.MustCompile(".\x08")
			o.Content = backspace.ReplaceAllString(stdin, "")
		} else {
			return fmt.Errorf("provide some content to display")
		}
	}

	m := model{
		viewport:            vp,
		help:                help.New(),
		content:             o.Content,
		origContent:         o.Content,
		showLineNumbers:     o.ShowLineNumbers,
		lineNumberStyle:     o.LineNumberStyle.ToLipgloss(),
		softWrap:            o.SoftWrap,
		matchStyle:          o.MatchStyle.ToLipgloss(),
		matchHighlightStyle: o.MatchHighlightStyle.ToLipgloss(),
		keymap:              defaultKeymap(),
		fixedHeight:         o.ViewportHeight,
	}

	ctx, cancel := timeout.Context(o.Timeout)
	defer cancel()

	// Use altscreen only for full-screen mode (height=0)
	opts := []tea.ProgramOption{
		tea.WithReportFocus(),
		tea.WithContext(ctx),
	}
	if o.ViewportHeight == 0 {
		opts = append(opts, tea.WithAltScreen())
	}

	_, err := tea.NewProgram(m, opts...).Run()
	if err != nil {
		return fmt.Errorf("unable to start program: %w", err)
	}

	return nil
}
