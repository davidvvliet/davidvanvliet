import { Command } from "./types";

const commands = new Map<string, Command>();

export function register(command: Command) {
  commands.set(command.name, command);
}

export function getCommand(name: string): Command | undefined {
  return commands.get(name);
}

export function getAllCommands(): Command[] {
  return Array.from(commands.values());
}
