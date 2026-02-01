package main

import (
	"fmt"
	"log"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// Styles for the UI
var (
	titleStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(lipgloss.Color("#FAFAFA")).
			Background(lipgloss.Color("#7D56F4")).
			Padding(0, 1).
			MarginBottom(1)

	labelStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#7D56F4")).
			Width(15).
			Bold(true)

	valueStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#FAFAFA"))

	infoBoxStyle = lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(lipgloss.Color("#7D56F4")).
			Padding(1, 2).
			Width(40)

	instructionStyle = lipgloss.NewStyle().
				Foreground(lipgloss.Color("#626262")).
				Italic(true).
				MarginTop(1)

	highlightStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#FF5F87")).
			Bold(true)
)

type model struct {
	mouseMsg tea.MouseMsg
	width    int
	height   int
}

func initialModel() model {
	return model{}
}

func (m model) Init() tea.Cmd {
	return nil
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.String() {
		case "q", "esc", "ctrl+c":
			return m, tea.Quit
		}

	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height

	case tea.MouseMsg:
		m.mouseMsg = msg
	}

	return m, nil
}

func (m model) View() string {
	var sb strings.Builder

	sb.WriteString(titleStyle.Render("Bubble Tea Mouse Demo"))
	sb.WriteString("\n\n")

	// Prepare data
	action := "None"
	button := "None"
	x, y := 0, 0
	mods := []string{}

	if m.mouseMsg.Type != tea.MouseUnknown {
		x = m.mouseMsg.X
		y = m.mouseMsg.Y

		// Determine action
		switch m.mouseMsg.Type {
		case tea.MouseLeft:
			button = "Left"
			action = "Press"
		case tea.MouseRight:
			button = "Right"
			action = "Press"
		case tea.MouseMiddle:
			button = "Middle"
			action = "Press"
		case tea.MouseWheelUp:
			button = "Wheel"
			action = "Scroll Up"
		case tea.MouseWheelDown:
			button = "Wheel"
			action = "Scroll Down"
		case tea.MouseMotion:
			action = "Motion"
		case tea.MouseRelease:
			action = "Release"
		}

		// Modifiers
		if m.mouseMsg.Shift {
			mods = append(mods, "Shift")
		}
		if m.mouseMsg.Alt {
			mods = append(mods, "Alt")
		}
		if m.mouseMsg.Ctrl {
			mods = append(mods, "Ctrl")
		}
	}

	modStr := strings.Join(mods, ", ")
	if modStr == "" {
		modStr = "None"
	}

	// Render the info box
	info := lipgloss.JoinVertical(lipgloss.Left,
		fmt.Sprintf("%s %s", labelStyle.Render("Position:"), valueStyle.Render(fmt.Sprintf("%d, %d", x, y))),
		fmt.Sprintf("%s %s", labelStyle.Render("Last Action:"), highlightStyle.Render(action)),
		fmt.Sprintf("%s %s", labelStyle.Render("Last Button:"), valueStyle.Render(button)),
		fmt.Sprintf("%s %s", labelStyle.Render("Modifiers:"), valueStyle.Render(modStr)),
	)

	sb.WriteString(infoBoxStyle.Render(info))
	sb.WriteString("\n")
	sb.WriteString(instructionStyle.Render("Move, click, and scroll! • Press 'q' or 'esc' to exit"))

	return sb.String()
}

func main() {
	p := tea.NewProgram(initialModel(), tea.WithMouseCellMotion())

	if _, err := p.Run(); err != nil {
		log.Fatalf("Error running program: %v", err)
	}
}
