import { Command } from "../types";
import { run } from "../run";
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
        ...posts.map((p) => `  ${run(`writing ${p.slug}`, p.slug)}${" ".repeat(maxSlug - p.slug.length)}    __GRAY__${p.title}  ${p.date}`),
      ];
    }

    const slug = args[0].toLowerCase();
    const post = getPost(slug);
    if (!post) return [`Unknown post: ${slug}. Type "${run("writing")}" to see available posts.`];

    usePageStore.getState().openPath(`/writing/${post.slug}`);
    return [`Opening "${post.title}"...`];
  },
  complete: (args) => (args.length <= 1 ? getAllPosts().map((p) => p.slug) : []),
};

register(writing);
