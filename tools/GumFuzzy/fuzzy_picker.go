package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"

	"github.com/charmbracelet/bubbles/list"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

var (
	titleStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(lipgloss.Color("#FAFAFA")).
			Background(lipgloss.Color("#7D56F4")).
			Padding(0, 1).
			MarginBottom(1)

	docStyle = lipgloss.NewStyle().Margin(1, 2)
)

type item struct {
	title, desc string
	path        string
	isDir       bool
}

func (i item) Title() string       { return i.title }
func (i item) Description() string { return i.desc }
func (i item) FilterValue() string { return i.title }

type model struct {
	list         list.Model
	currentDir   string
	selectedFile string
	quitting     bool
	height       int
	width        int
}

func getItems(dir string) []list.Item {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil
	}

	var items []list.Item
	if dir != "/" {
		items = append(items, item{
			title: "..",
			desc:  "Parent Directory",
			path:  filepath.Dir(dir),
			isDir: true,
		})
	}

	for _, entry := range entries {
		info, _ := entry.Info()
		prefix := "📄 "
		if entry.IsDir() {
			prefix = "📁 "
		}
		items = append(items, item{
			title: prefix + entry.Name(),
			desc:  fmt.Sprintf("%s | %d bytes", info.ModTime().Format("2006-01-02"), info.Size()),
			path:  filepath.Join(dir, entry.Name()),
			isDir: entry.IsDir(),
		})
	}
	return items
}

func (m model) Init() tea.Cmd {
	return nil
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		if msg.String() == "ctrl+c" || msg.String() == "q" {
			m.quitting = true
			return m, tea.Quit
		}

		if msg.String() == "enter" {
			i, ok := m.list.SelectedItem().(item)
			if ok {
				if i.isDir {
					m.currentDir = i.path
					m.list.SetItems(getItems(m.currentDir))
					m.list.ResetFilter()
					return m, nil
				} else {
					m.selectedFile = i.path
					return m, tea.Quit
				}
			}
		}

	case tea.WindowSizeMsg:
		h, v := docStyle.GetFrameSize()
		m.width = msg.Width
		// If we are in AltScreen, we use the full height.
		// If not, we might use a fixed height.
		m.list.SetSize(msg.Width-h, msg.Height-v)
	}

	var cmd tea.Cmd
	m.list, cmd = m.list.Update(msg)
	return m, cmd
}

func (m model) View() string {
	if m.quitting || m.selectedFile != "" {
		return ""
	}
	return docStyle.Render(m.list.View())
}

func main() {
	var heightFlag int
	flag.IntVar(&heightFlag, "height", 0, "Height of the picker (default: full screen)")
	flag.Parse()

	home, _ := os.UserHomeDir()
	startDir := filepath.Join(home, "Downloads")
	if _, err := os.Stat(startDir); err != nil {
		startDir = home
	}

	items := getItems(startDir)
	l := list.New(items, list.NewDefaultDelegate(), 0, 0)
	l.Title = "CAREER AI: SELECT FILE"
	l.SetShowStatusBar(true)
	l.SetFilteringEnabled(true)

	m := model{
		list:       l,
		currentDir: startDir,
	}

	// Open TTY for TUI communication
	f, err := os.OpenFile("/dev/tty", os.O_RDWR, 0)
	if err != nil {
		// Fallback to stderr if /dev/tty fails
		f = os.Stderr
	}
	defer f.Close()

	opts := []tea.ProgramOption{
		tea.WithInput(f),
		tea.WithOutput(f),
	}

	// If height is 0, use AltScreen (full terminal)
	if heightFlag == 0 {
		opts = append(opts, tea.WithAltScreen())
	}

	p := tea.NewProgram(m, opts...)

	finalModel, err := p.Run()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	if fm, ok := finalModel.(model); ok && fm.selectedFile != "" {
		// Output ONLY the final path to stdout
		fmt.Println(fm.selectedFile)
	}
}
