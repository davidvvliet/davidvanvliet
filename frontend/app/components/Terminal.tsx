"use client";

import { useState, useRef, useEffect, KeyboardEvent } from "react";
import styles from "./Terminal.module.css";

export default function Terminal() {
  const [lines, setLines] = useState<string[]>([]);
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines]);

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      setLines((prev) => [...prev, input]);
      setInput("");
    }
  };

  return (
    <div className={styles.terminal} onClick={() => inputRef.current?.focus()}>
      {lines.map((line, i) => (
        <div key={i} className={styles.line}>
          <span className={styles.prompt}>&gt;</span> {line}
        </div>
      ))}
      <div className={styles.inputRow}>
        <span className={styles.prompt}>&gt;</span>
        <div className={styles.inputWrapper}>
          <span className={styles.inputText}>{input}</span>
          <span className={styles.caret} />
          <input
            ref={inputRef}
            className={styles.hiddenInput}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
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
