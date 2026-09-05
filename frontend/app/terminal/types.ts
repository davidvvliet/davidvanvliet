export interface Command {
  name: string;
  aliases?: string[];
  description: string;
  hidden?: boolean;
  /** Grouping in `help`: 'explore' for the solar system; anything else is general. */
  category?: 'explore';
  execute: (args: string[]) => string[];
  /** Optional: return completion candidates for the argument at args.length - 1. */
  complete?: (args: string[]) => string[];
}
