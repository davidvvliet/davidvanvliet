"use client";

import React, { useState, useRef, useEffect, KeyboardEvent } from "react";
import styles from "./Terminal.module.css";
import { getCommand, getAllCommands } from "../terminal";

type Line = { text: string; type: "input" | "output" };

// Turn bare http(s) URLs in output text into clickable links.
const URL_RE = /(https?:\/\/[^\s]+)/g;
function linkify(text: string): React.ReactNode {
  const parts = text.split(URL_RE);
  if (parts.length === 1) return text;
  return parts.map((part, i) =>
    /^https?:\/\//.test(part) ? (
      <a key={i} href={part} target="_blank" rel="noopener noreferrer" className={styles.link}>{part}</a>
    ) : (
      part
    )
  );
}

export default function Terminal() {
  const [lines, setLines] = useState<Line[]>([]);
  const [input, setInput] = useState("");
  const [cursorPos, setCursorPos] = useState(0);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  // Command history for Up/Down. `historyIndex` is where we are while browsing
  // (history.length = not browsing); `draft` is what was typed before browsing.
  const historyRef = useRef<string[]>([]);
  const historyIndexRef = useRef<number>(0);
  const draftRef = useRef<string>("");

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines]);

  const syncCursor = () => {
    const pos = inputRef.current?.selectionStart ?? input.length;
    setCursorPos(pos);
  };

  const setInputAndCursor = (value: string) => {
    setInput(value);
    setCursorPos(value.length);
    requestAnimationFrame(() => {
      inputRef.current?.setSelectionRange(value.length, value.length);
    });
  };

  const handleTab = () => {
    const words = input.split(" ");
    const isCommandWord = words.length === 1;
    const current = words[words.length - 1];
    const prefix = current.toLowerCase();

    let candidates: string[];
    if (isCommandWord) {
      if (!prefix) return;
      candidates = getAllCommands()
        .filter((cmd) => !cmd.hidden)
        .map((cmd) => cmd.name);
    } else {
      const command = getCommand(words[0].toLowerCase());
      if (!command?.complete) return;
      candidates = command.complete(words.slice(1));
    }

    const matches = candidates
      .filter((c) => c.toLowerCase().startsWith(prefix))
      .sort();
    if (matches.length === 0) return;

    const replaceCurrent = (value: string) =>
      setInputAndCursor([...words.slice(0, -1), value].join(" "));

    if (matches.length === 1) {
      replaceCurrent(`${matches[0]} `);
      return;
    }

    // Fill in the longest common prefix shared by all matches.
    let common = matches[0];
    for (const name of matches.slice(1)) {
      let i = 0;
      while (i < common.length && i < name.length && common[i] === name[i]) i++;
      common = common.slice(0, i);
    }

    if (common.length > current.length) {
      replaceCurrent(common);
    } else {
      // Nothing more to fill in: list the candidates, like a shell does.
      setLines((prev) => [
        ...prev,
        { text: `> ${input}`, type: "input" },
        { text: matches.join("  "), type: "output" },
      ]);
    }
  };

  const browseHistory = (direction: -1 | 1) => {
    const history = historyRef.current;
    if (history.length === 0) return;
    const atEnd = historyIndexRef.current === history.length;
    if (atEnd && direction === 1) return; // nothing newer
    if (atEnd) draftRef.current = input; // leaving the live line: remember it
    const next = Math.max(0, Math.min(history.length, historyIndexRef.current + direction));
    historyIndexRef.current = next;
    setInputAndCursor(next === history.length ? draftRef.current : history[next]);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Tab") {
      e.preventDefault();
      handleTab();
      return;
    }

    if (e.key === "ArrowUp" || e.key === "ArrowDown") {
      e.preventDefault(); // otherwise the caret jumps to the start/end
      browseHistory(e.key === "ArrowUp" ? -1 : 1);
      return;
    }

    if (e.key === "Enter") {
      const trimmed = input.trim();
      if (!trimmed) {
        setLines((prev) => [...prev, { text: ">", type: "input" }]);
        setInput("");
        setCursorPos(0);
        return;
      }

      // Record in history (skip consecutive duplicates) and reset browsing.
      const history = historyRef.current;
      if (history[history.length - 1] !== trimmed) history.push(trimmed);
      historyIndexRef.current = history.length;
      draftRef.current = "";

      const [name, ...args] = trimmed.split(" ");
      const command = getCommand(name.toLowerCase());

      const output = command
        ? command.execute(args)
        : [`Unknown command: ${name}. Type "help" for available commands.`];

      if (output.includes("__CLEAR__")) {
        setLines([]);
      } else {
        setLines((prev) => [
          ...prev,
          { text: `> ${trimmed}`, type: "input" },
          ...output.map((text) => ({ text, type: "output" as const })),
        ]);
      }
      setInput("");
      setCursorPos(0);
    }
  };

  const beforeCaret = input.slice(0, cursorPos);
  const afterCaret = input.slice(cursorPos);

  return (
    <div className={styles.terminal} onClick={() => inputRef.current?.focus()}>
      {lines.map((line, i) =>
        line.type === "output" && line.text.startsWith("__IMG__") ? (
          <div key={i} className={styles.imageRow}>
            {line.text.slice(7).split(",").map((src, j) => (
              <img key={j} src={src} alt="" className={styles.poster} />
            ))}
          </div>
        ) : line.type === "output" && line.text.startsWith("__COL__") ? (
          <div key={i} className={styles.colRow}>
            <span className={`${styles.colLeft} ${styles.output}`}>{line.text.split("__COL__")[1]}</span>
            <span className={styles.dim}>{line.text.split("__COL__")[2]}</span>
          </div>
        ) : (
          <div key={i} className={`${styles.line} ${line.type === "output" ? styles.output : ""}`}>
            {line.type === "input" && line.text.startsWith(">") ? (
              <>
                <span className={styles.prompt}>&gt;</span>
                {line.text.slice(2)}
              </>
            ) : line.text.includes("__GRAY__") ? (
              <>
                {linkify(line.text.split("__GRAY__")[0])}
                <span className={styles.gray}>{linkify(line.text.split("__GRAY__")[1])}</span>
              </>
            ) : line.text.includes("__DIM__") ? (
              <>
                {linkify(line.text.split("__DIM__")[0])}
                <span className={styles.dim}>{linkify(line.text.split("__DIM__")[1])}</span>
              </>
            ) : (
              linkify(line.text)
            )}
          </div>
        )
      )}
      <div className={styles.inputRow}>
        <span className={styles.prompt}>&gt;</span>
        <div className={styles.inputWrapper}>
          <span className={styles.inputText}>{beforeCaret}</span>
          <span className={styles.caret}>{input[cursorPos] ?? " "}</span>
          <span className={styles.inputText}>{afterCaret.slice(1)}</span>
          <input
            ref={inputRef}
            className={styles.hiddenInput}
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              setCursorPos(e.target.selectionStart ?? e.target.value.length);
              historyIndexRef.current = historyRef.current.length; // typing leaves browse mode
            }}
            onKeyDown={handleKeyDown}
            onKeyUp={syncCursor}
            onClick={syncCursor}
            autoFocus
            spellCheck={false}
            autoComplete="off"
          />
        </div>
      </div>
      <div ref={bottomRef} />
    </div>
  );
}
