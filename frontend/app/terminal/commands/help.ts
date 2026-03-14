import { Command } from "../types";
import { register, getAllCommands } from "../registry";

const help: Command = {
  name: "help",
  description: "List available commands",
  execute: () => {
    const commands = getAllCommands().filter((cmd) => !cmd.hidden);
    const maxLen = Math.max(...commands.map((cmd) => cmd.name.length));
    return [
      "Available commands:",
      ...commands.map((cmd) => `  ${cmd.name.padEnd(maxLen)}    ${cmd.description}`),
    ];
  },
};

register(help);
