import { Command } from "../types";
import { register } from "../registry";

const clear: Command = {
  name: "clear",
  description: "Clear the terminal",
  execute: () => ["__CLEAR__"],
};

register(clear);
