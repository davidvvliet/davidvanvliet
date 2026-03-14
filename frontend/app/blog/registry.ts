import { BlogPost } from "./types";

const posts = new Map<string, BlogPost>();

export function registerPost(post: BlogPost) {
  posts.set(post.slug.toLowerCase(), post);
}

export function getPost(slug: string): BlogPost | undefined {
  return posts.get(slug.toLowerCase());
}

export function getAllPosts(): BlogPost[] {
  return Array.from(posts.values());
}
