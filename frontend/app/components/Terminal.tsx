"use client";

import { useState, useRef, useEffect, KeyboardEvent } from "react";
import styles from "./Terminal.module.css";
import { getCommand } from "../terminal";

type Line = { text: string; type: "input" | "output" };

export default function Terminal() {
  const [lines, setLines] = useState<Line[]>([]);
  const [input, setInput] = useState("");
  const [cursorPos, setCursorPos] = useState(0);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines]);

  const syncCursor = () => {
    const pos = inputRef.current?.selectionStart ?? input.length;
    setCursorPos(pos);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      const trimmed = input.trim();
      if (!trimmed) {
        setLines((prev) => [...prev, { text: ">", type: "input" }]);
        setInput("");
        setCursorPos(0);
        return;
      }

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
                {line.text.split("__GRAY__")[0]}
                <span className={styles.gray}>{line.text.split("__GRAY__")[1]}</span>
              </>
            ) : line.text.includes("__DIM__") ? (
              <>
                {line.text.split("__DIM__")[0]}
                <span className={styles.dim}>{line.text.split("__DIM__")[1]}</span>
              </>
            ) : (
              line.text
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
