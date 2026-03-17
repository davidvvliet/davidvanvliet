import { Command } from "../types";
import { register, getAllCommands } from "../registry";

const help: Command = {
  name: "help",
  aliases: ["h"],
  description: "List available commands",
  execute: () => {
    const commands = getAllCommands().filter((cmd) => !cmd.hidden);
    const label = (cmd: (typeof commands)[0]) =>
      cmd.aliases?.length ? `${cmd.name} | ${cmd.aliases.join(" | ")}` : cmd.name;
    const maxLen = Math.max(...commands.map((cmd) => label(cmd).length));
    return [
      "Available commands:",
      ...commands.map((cmd) => `  ${label(cmd).padEnd(maxLen)}    __DIM__${cmd.description}`),
    ];
  },
};

register(help);
