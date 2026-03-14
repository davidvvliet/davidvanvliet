import { Command } from "../types";
import { register } from "../registry";
import { getAllPosts, getPost } from "../../blog";
import { usePageStore } from "../../store/pageStore";

const blog: Command = {
  name: "blog",
  description: "List or open blog posts",
  execute: (args) => {
    if (!args[0]) {
      const posts = getAllPosts();
      if (posts.length === 0) return ["No blog posts yet."];
      const maxTitle = Math.max(...posts.map((p) => p.title.length));
      return [
        "Usage: blog <name>",
        "",
        "Blog posts:",
        ...posts.map((p) => `  ${p.title.padEnd(maxTitle)}    ${p.date}`),
      ];
    }

    const slug = args[0].toLowerCase();
    const post = getPost(slug);
    if (!post) return [`Unknown post: ${slug}. Type "blog" to see available posts.`];

    usePageStore.getState().setBlogPost(slug);
    usePageStore.getState().setLeftPanel("blog");
    return [`Opening "${post.title}"...`];
  },
};

register(blog);
