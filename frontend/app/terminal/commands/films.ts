import { Command } from "../types";
import { register } from "../registry";

const films: Command = {
  name: "films",
  description: "Good films",
  execute: () => {
    return ["__IMG__/2001.jpg,/bladerunner.jpg,/drstrangelove.jpg"];
  },
};

register(films);
