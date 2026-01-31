package main

import (
	"fmt"
	"os"
	"regexp"
	"strings"

	"github.com/charmbracelet/bubbles/textinput"
	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/glamour"
	"github.com/charmbracelet/lipgloss"
	zone "github.com/lrstanley/bubblezone"
)

// Styles
var (
	titleStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(lipgloss.Color("#FAFAFA")).
			Background(lipgloss.Color("#7D56F4")).
			Padding(0, 1)

	statusStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#626262")).
			Background(lipgloss.Color("#1a1a1a")).
			Padding(0, 1)

	placeholderStyle = lipgloss.NewStyle().
				Foreground(lipgloss.Color("#FF5F87")).
				Background(lipgloss.Color("#3C3C3C")).
				Bold(true)

	activePlaceholderStyle = lipgloss.NewStyle().
				Foreground(lipgloss.Color("#FAFAFA")).
				Background(lipgloss.Color("#F25D94")).
				Bold(true)

	filledStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#73F59F")).
			Bold(true)

	inputBoxStyle = lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(lipgloss.Color("#F25D94")).
			Padding(0, 1)

	helpStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#626262"))
)

// Placeholder represents a fillable field
type Placeholder struct {
	ID       string
	Original string
	Value    string
}

type model struct {
	width        int
	height       int
	letterText   string
	filePath     string
	placeholders []Placeholder
	editing      int
	textInput    textinput.Model
	viewport     viewport.Model
	ready        bool
	saved        bool
	glamourStyle string
}

func initialModel(letterPath string) model {
	content, err := os.ReadFile(letterPath)
	if err != nil {
		content = []byte(defaultLetter)
	}

	letterText := string(content)

	// Find all placeholders
	re := regexp.MustCompile(`\[[^\]]+\]`)
	matches := re.FindAllString(letterText, -1)

	seen := make(map[string]bool)
	var placeholders []Placeholder
	for i, match := range matches {
		if !seen[match] {
			seen[match] = true
			placeholders = append(placeholders, Placeholder{
				ID:       fmt.Sprintf("ph-%d", i),
				Original: match,
				Value:    "",
			})
		}
	}

	ti := textinput.New()
	ti.Placeholder = "Type replacement..."
	ti.CharLimit = 100
	ti.Width = 50

	return model{
		letterText:   letterText,
		filePath:     letterPath,
		placeholders: placeholders,
		editing:      -1,
		textInput:    ti,
		glamourStyle: "dark",
	}
}

func (m model) Init() tea.Cmd {
	return nil
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	var cmds []tea.Cmd

	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.String() {
		case "ctrl+c", "q":
			if m.editing == -1 {
				return m, tea.Quit
			}
		case "esc":
			if m.editing != -1 {
				m.editing = -1
				m.textInput.Blur()
			}
		case "enter":
			if m.editing != -1 {
				m.placeholders[m.editing].Value = m.textInput.Value()
				m.editing = -1
				m.textInput.Blur()
				m.textInput.SetValue("")
				m.saved = false
			}
		case "ctrl+s":
			m.saveToFile()
			m.saved = true
		case "tab":
			if m.editing == -1 {
				for i, ph := range m.placeholders {
					if ph.Value == "" {
						m.editing = i
						m.textInput.SetValue("")
						m.textInput.Placeholder = fmt.Sprintf("Enter %s", strings.Trim(ph.Original, "[]"))
						m.textInput.Focus()
						return m, textinput.Blink
					}
				}
			}
		}

	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height

		headerHeight := 3
		footerHeight := 4
		if m.editing != -1 {
			footerHeight = 6
		}

		if !m.ready {
			m.viewport = viewport.New(msg.Width-4, msg.Height-headerHeight-footerHeight)
			m.viewport.YPosition = headerHeight
			m.ready = true
		} else {
			m.viewport.Width = msg.Width - 4
			m.viewport.Height = msg.Height - headerHeight - footerHeight
		}

	case tea.MouseMsg:
		if msg.Action == tea.MouseActionRelease && msg.Button == tea.MouseButtonLeft {
			for i, ph := range m.placeholders {
				if zone.Get(ph.ID).InBounds(msg) {
					m.editing = i
					m.textInput.SetValue(ph.Value)
					m.textInput.Placeholder = fmt.Sprintf("Enter %s", strings.Trim(ph.Original, "[]"))
					m.textInput.Focus()
					return m, textinput.Blink
				}
			}
		}

		// Handle viewport scrolling
		var cmd tea.Cmd
		m.viewport, cmd = m.viewport.Update(msg)
		cmds = append(cmds, cmd)
	}

	// Update text input if editing
	if m.editing != -1 {
		var cmd tea.Cmd
		m.textInput, cmd = m.textInput.Update(msg)
		cmds = append(cmds, cmd)
	}

	// Update viewport for scrolling
	if m.editing == -1 {
		var cmd tea.Cmd
		m.viewport, cmd = m.viewport.Update(msg)
		cmds = append(cmds, cmd)
	}

	return m, tea.Batch(cmds...)
}

func (m model) renderContent() string {
	// Build letter with clickable placeholders
	letter := m.letterText

	for _, ph := range m.placeholders {
		var replacement string
		if ph.Value != "" {
			replacement = zone.Mark(ph.ID, filledStyle.Render(ph.Value))
		} else if m.editing != -1 && m.placeholders[m.editing].ID == ph.ID {
			replacement = zone.Mark(ph.ID, activePlaceholderStyle.Render(ph.Original))
		} else {
			replacement = zone.Mark(ph.ID, placeholderStyle.Render(ph.Original))
		}
		letter = strings.Replace(letter, ph.Original, replacement, 1)
	}

	// Render with glamour for nice markdown
	rendered, err := glamour.Render(letter, m.glamourStyle)
	if err != nil {
		return letter
	}

	return rendered
}

func (m model) View() string {
	if !m.ready {
		return "Loading..."
	}

	var sb strings.Builder

	// Header
	title := titleStyle.Render("📝 Cover Letter Editor")
	file := statusStyle.Render(m.filePath)
	header := lipgloss.JoinHorizontal(lipgloss.Center, title, " ", file)
	sb.WriteString(header)
	sb.WriteString("\n\n")

	// Update viewport content
	m.viewport.SetContent(m.renderContent())

	// Viewport (scrollable content)
	sb.WriteString(m.viewport.View())
	sb.WriteString("\n")

	// Footer
	if m.editing != -1 {
		sb.WriteString(inputBoxStyle.Render(
			fmt.Sprintf("✏️  %s: %s",
				m.placeholders[m.editing].Original,
				m.textInput.View(),
			),
		))
		sb.WriteString("\n")
		sb.WriteString(helpStyle.Render("Enter = save • Esc = cancel"))
	} else {
		filled := 0
		for _, ph := range m.placeholders {
			if ph.Value != "" {
				filled++
			}
		}

		status := fmt.Sprintf("📊 %d/%d filled", filled, len(m.placeholders))
		if m.saved {
			status += " • ✅ Saved!"
		}
		sb.WriteString(helpStyle.Render(status))
		sb.WriteString("\n")
		sb.WriteString(helpStyle.Render("🖱️ Click placeholder • Tab = next • Ctrl+S = save • Q = quit • ↑↓ = scroll"))
	}

	return zone.Scan(sb.String())
}

func (m *model) saveToFile() {
	result := m.letterText
	for _, ph := range m.placeholders {
		if ph.Value != "" {
			result = strings.ReplaceAll(result, ph.Original, ph.Value)
		}
	}

	// Save as _filled version
	outPath := strings.TrimSuffix(m.filePath, ".md") + "_filled.md"
	os.WriteFile(outPath, []byte(result), 0644)
}

const defaultLetter = `# Cover Letter

[Your Name]
[Date]

Dear Hiring Manager,

As a builder, I bring hands-on experience in system software and display technologies to drive impactful solutions.

This role aligns with my passion for system software and display technologies, offering a unique opportunity to shape the future of consumer hardware.

I am eager to contribute my expertise and align with [Company]'s mission to deliver industry-leading solutions.

Sincerely,
[Your Name]
`

func main() {
	zone.NewGlobal()

	filePath := "cover_letter.md"
	if len(os.Args) > 1 {
		filePath = os.Args[1]
	}

	p := tea.NewProgram(
		initialModel(filePath),
		tea.WithAltScreen(),
		tea.WithMouseCellMotion(),
	)

	if _, err := p.Run(); err != nil {
		fmt.Printf("Error: %v\n", err)
		os.Exit(1)
	}
}
