import { Command } from "../types";
import { register } from "../registry";
import { usePageStore } from "../../store/pageStore";

const resume: Command = {
  name: "resume",
  description: "Open my resume",
  execute: () => {
    usePageStore.getState().setLeftPanel("resume");
    return ["Loading resume..."];
  },
};

register(resume);
