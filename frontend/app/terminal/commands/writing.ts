import { Command } from "../types";
import { register } from "../registry";
import { getAllPosts, getPost } from "../../writing";
import { usePageStore } from "../../store/pageStore";

const writing: Command = {
  name: "writing",
  aliases: ["w"],
  description: "List or open writing",
  execute: (args) => {
    if (!args[0]) {
      const posts = getAllPosts();
      if (posts.length === 0) return ["Nothing here yet."];
      const maxSlug = Math.max(...posts.map((p) => p.slug.length));
      return [
        "__DIM__Usage: writing | w <post>",
        "",
        "Writing:",
        ...posts.map((p) => `  ${p.slug.padEnd(maxSlug)}    __GRAY__${p.title}  ${p.date}`),
      ];
    }

    const slug = args[0].toLowerCase();
    const post = getPost(slug);
    if (!post) return [`Unknown post: ${slug}. Type "writing" to see available posts.`];

    usePageStore.getState().setBlogPost(slug);
    usePageStore.getState().setLeftPanel("blog");
    return [`Opening "${post.title}"...`];
  },
  complete: (args) => (args.length <= 1 ? getAllPosts().map((p) => p.slug) : []),
};

register(writing);
