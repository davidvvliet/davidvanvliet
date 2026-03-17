export interface Command {
  name: string;
  aliases?: string[];
  description: string;
  hidden?: boolean;
  execute: (args: string[]) => string[];
}
