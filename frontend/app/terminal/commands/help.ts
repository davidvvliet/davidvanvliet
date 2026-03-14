import { Command } from "../types";
import { register, getAllCommands } from "../registry";

const help: Command = {
  name: "help",
  description: "List available commands",
  execute: () => {
    const commands = getAllCommands();
    return [
      "Available commands:",
      ...commands.filter((cmd) => !cmd.hidden).map((cmd) => `  ${cmd.name} - ${cmd.description}`),
    ];
  },
};

register(help);
