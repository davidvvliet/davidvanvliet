export interface BlogPost {
  slug: string;
  title: string;
  date: string;
  subtitle?: string;
  image?: string; // under the title, as on Substack: a path in public/
  content: string;
}
