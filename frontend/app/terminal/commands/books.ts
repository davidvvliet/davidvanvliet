import { Command } from "../types";
import { register } from "../registry";

const books: Command = {
  name: "books",
  description: "Good books",
  execute: () => {
    return ["__IMG__/comc.jpg,/atlasshrugged.jpg"];
  },
};

register(books);
