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
    const rows = (list: typeof commands) => list.map((cmd) => `__COL__${label(cmd)}__COL__${cmd.description}`);
    const general = commands.filter((cmd) => cmd.category !== "explore");
    const explore = commands.filter((cmd) => cmd.category === "explore");
    return [
      "General commands:",
      ...rows(general),
      "",
      "Explore commands:",
      ...rows(explore),
      "",
      "__GRAY__There are also hidden commands!",
    ];
  },
};

register(help);
