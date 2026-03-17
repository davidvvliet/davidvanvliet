import { Command } from "../types";
import { register } from "../registry";
import { getAllPosts, getPost } from "../../blog";
import { usePageStore } from "../../store/pageStore";

const blog: Command = {
  name: "blog",
  aliases: ["b"],
  description: "List or open blog posts",
  execute: (args) => {
    if (!args[0]) {
      const posts = getAllPosts();
      if (posts.length === 0) return ["No blog posts yet."];
      const maxTitle = Math.max(...posts.map((p) => p.title.length));
      return [
        "__DIM__Usage: blog | b <post>",
        "",
        "Blog posts:",
        ...posts.map((p) => `  ${p.title.padEnd(maxTitle)}    __GRAY__${p.date}`),
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
