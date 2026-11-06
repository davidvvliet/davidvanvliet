import { Command } from "../types";
import { register } from "../registry";

const admired: [string, string][] = [
  ["Isaac Newton", "For sparking the enlightenment through the power of his ideas alone"],
  ["Charles Darwin", "For defending his earth shattering insight in the face of dogma"],
  ["David Deutsch", "For his always good-faith and correct optimism"],
  ["Peter Thiel", "For his individualism and for taking the future seriously"],
  ["Elon Musk", "For taking the strides of technological progress in an otherwise stale world"],
  ["John D. Rockefeller", "For freeing us from the tyranny of night with cheap light"],
  ["Mark Zuckerberg", "For keeping the crown that he was given"],
  ["Bill Gates", "For starting the revolution of bits"],
  ["Edwin Land", "For coloring the world"],
];

const people: Command = {
  name: "people",
  description: "People I admire",
  execute: () => {
    const width = Math.max(...admired.map(([name]) => name.length));
    return [
      "People I admire:",
      "",
      ...admired.map(([name, why]) => `  ${name}${" ".repeat(width - name.length)}    __GRAY__${why}`),
    ];
  },
};

register(people);
