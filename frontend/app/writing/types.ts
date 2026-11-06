export interface BlogPost {
  slug: string;
  title: string;
  shortTitle?: string; // in the terminal list, when the title is too long
  date: string;
  subtitle?: string;
  image?: string; // under the title, as on Substack: a path in public/
  content: string;
}
