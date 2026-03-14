export interface Command {
  name: string;
  description: string;
  hidden?: boolean;
  execute: (args: string[]) => string[];
}
