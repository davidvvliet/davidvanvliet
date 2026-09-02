export interface Command {
  name: string;
  aliases?: string[];
  description: string;
  hidden?: boolean;
  execute: (args: string[]) => string[];
  /** Optional: return completion candidates for the argument at args.length - 1. */
  complete?: (args: string[]) => string[];
}
