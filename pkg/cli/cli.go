package cli

import (
	"bufio"
	"flag"
	"fmt"
	"os"
	"strings"
)

// CLI represents the command-line interface.
type CLI struct {
	name     string
	version  string
	commands map[string]*Command
	out      *bufio.Writer
	err      *bufio.Writer
}

// Command represents a subcommand.
type Command struct {
	Name        string
	Description string
	Usage       string
	Flags       *flag.FlagSet
	Action      func(args []string) error
}

// NewCLI creates a new CLI instance.
func NewCLI(name, version string) *CLI {
	return &CLI{
		name:     name,
		version:  version,
		commands: make(map[string]*Command),
		out:      bufio.NewWriter(os.Stdout),
		err:      bufio.NewWriter(os.Stderr),
	}
}

// AddCommand registers a new subcommand.
func (c *CLI) AddCommand(cmd *Command) {
	c.commands[cmd.Name] = cmd
}

// Run executes the CLI with the given arguments.
func (c *CLI) Run(args []string) error {
	if len(args) == 0 {
		return c.printHelp()
	}

	cmdName := args[0]
	cmd, ok := c.commands[cmdName]
	if !ok {
		return fmt.Errorf("unknown command: %s", cmdName)
	}

	if cmd.Flags != nil {
		cmd.Flags.Usage = func() {
			fmt.Fprintf(c.err, "Usage: %s %s %s\n", c.name, cmd.Name, cmd.Usage)
			cmd.Flags.PrintDefaults()
			c.err.Flush()
			os.Exit(1)
		}
		if err := cmd.Flags.Parse(args[1:]); err != nil {
			return err
		}
	}

	actionArgs := args[1:]
	if cmd.Flags != nil {
		actionArgs = cmd.Flags.Args()
	}
	if err := cmd.Action(actionArgs); err != nil {
		return fmt.Errorf("%s: %w", cmdName, err)
	}

	c.out.Flush()
	c.err.Flush()
	return nil
}

// Printf prints to stdout.
func (c *CLI) Printf(format string, a ...interface{}) {
	fmt.Fprintf(c.out, format, a...)
}

// Println prints a line to stdout.
func (c *CLI) Println(a ...interface{}) {
	fmt.Fprintln(c.out, a...)
}

// Fatalf prints an error and exits.
func (c *CLI) Fatalf(format string, a ...interface{}) {
	fmt.Fprintf(c.err, "error: "+format+"\n", a...)
	c.err.Flush()
	os.Exit(1)
}

// printHelp prints the help message.
func (c *CLI) printHelp() error {
	c.Println(fmt.Sprintf("%s %s", c.name, c.version))
	c.Println("Usage: astrovox <command> [options]")
	c.Println()
	c.Println("Commands:")
	for _, cmd := range c.commands {
		c.Printf("  %-10s %s\n", cmd.Name, cmd.Description)
	}
	c.Println()
	c.Println("Run 'astrovox <command> --help' for more information on a command.")
	return nil
}

// ParseEnvFlags parses environment variables for configuration.
func ParseEnvFlags(prefix string) map[string]string {
	env := make(map[string]string)
	for _, e := range os.Environ() {
		parts := strings.SplitN(e, "=", 2)
		if len(parts) != 2 {
			continue
		}
		key := parts[0]
		value := parts[1]
		if strings.HasPrefix(key, prefix) {
			env[key] = value
		}
	}
	return env
}
