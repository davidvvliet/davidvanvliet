// Clickable commands in terminal output. `run("writing moon", "moon")` renders
// "moon"; clicking it types "writing moon" into the prompt and presses Enter.
// Works inside any output line (plain, __DIM__, __GRAY__, __COL__ columns, ...).
export function run(command: string, label: string = command): string {
  return `[[${command}|${label}]]`;
}

// Splitting on this gives [text, command, label, text, command, label, ..., text].
export const RUN_SPLIT = /\[\[([^\]|]+)\|([^\]]*)\]\]/;
