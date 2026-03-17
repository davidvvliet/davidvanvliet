import { Command } from "./types";

const commands = new Map<string, Command>();

export function register(command: Command) {
  commands.set(command.name, command);
  command.aliases?.forEach((alias) => commands.set(alias, command));
}

export function getCommand(name: string): Command | undefined {
  return commands.get(name);
}

export function getAllCommands(): Command[] {
  return Array.from(commands.entries())
    .filter(([key, cmd]) => key === cmd.name)
    .map(([, cmd]) => cmd);
}
