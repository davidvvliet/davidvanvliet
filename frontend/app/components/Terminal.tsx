"use client";

import React, { useState, useRef, useEffect, KeyboardEvent } from "react";
import styles from "./Terminal.module.css";
import { getCommand, getAllCommands } from "../terminal";
import { run, RUN_SPLIT } from "../terminal/run";
import { usePageStore } from "../store/pageStore";
import dynamic from "next/dynamic";

// Model lines bring in three.js and the viewer only when one appears.
const ModelLine = dynamic(() => import("./ModelLine"), { ssr: false });

type Line = { text: string; type: "input" | "output"; restored?: boolean };

// The last few lines and typed commands survive reloads (per browser).
const HISTORY_KEY = "terminal-history";
const HISTORY_LINES = 50;
const HISTORY_COMMANDS = 50;

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

// Output text with clickable commands (see terminal/run.ts); the rest is linkified.
function rich(text: string, onRun: (command: string) => void): React.ReactNode {
  const parts = text.split(new RegExp(RUN_SPLIT.source, "g"));
  if (parts.length === 1) return linkify(text);
  const out: React.ReactNode[] = [];
  for (let i = 0; i < parts.length; i += 3) {
    if (parts[i]) out.push(<React.Fragment key={i}>{linkify(parts[i])}</React.Fragment>);
    if (i + 1 < parts.length) {
      const command = parts[i + 1];
      out.push(
        <span
          key={i + 1}
          role="button"
          tabIndex={-1}
          className={styles.run}
          onClick={(e) => { e.stopPropagation(); onRun(command); }}
        >{parts[i + 2]}</span>
      );
    }
  }
  return out;
}

// Typing speed for a clicked command: about a quarter second in all.
const TYPE_TOTAL_MS = 250;
const TYPE_MIN_STEP_MS = 12;
const TYPE_MAX_STEP_MS = 35;

// A video line. Fresh: autoplays at 3x and scrolls into view once it has a size;
// when it ends, its source is dropped (releasing the decoder and buffers) and the
// poster, the last frame, stays. Restored from a previous visit: poster only,
// nothing is fetched.
function VideoLine({ src: spec, restored, onSized }: { src: string; restored?: boolean; onSized: () => void }) {
  const [done, setDone] = useState(!!restored);
  // Options after "@": a number = free-running at that playback rate (default 3);
  // "jd:<startJD>" = locked to the simulated clock, whose date the first frame shows;
  // "sound" = play with audio (works because typing the command counted as a gesture).
  const [src, ...opts] = spec.split("@");
  const jdOpt = opts.find((o) => o.startsWith("jd:"));
  const startJD = jdOpt ? parseFloat(jdOpt.slice(3)) : null;
  const rateOpt = opts.find((o) => /^[\d.]+$/.test(o));
  const rate = rateOpt ? parseFloat(rateOpt) : 3;
  const sound = opts.includes("sound");
  const poster = src.replace(/\.webm$/, ".jpg");
  const ref = useRef<HTMLVideoElement>(null);
  // Countdown of the footage left, with milliseconds, on the bottom-right corner.
  const countRef = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    if (done) return;
    let raf = 0;
    const tick = () => {
      const el = ref.current, out = countRef.current;
      if (el && out && el.duration) {
        const left = Math.max(0, el.duration - el.currentTime);
        const m = Math.floor(left / 60), s = Math.floor(left % 60), ms = Math.floor((left % 1) * 1000);
        out.textContent = `${m}:${String(s).padStart(2, "0")}.${String(ms).padStart(3, "0")}`;
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [done]);
  // Clock lock: keep the video where the clock says, at the clock's current rate. If the
  // browser pauses it (scrolled away, tab hidden), it resumes and re-seeks into step.
  useEffect(() => {
    if (startJD === null || done) return;
    let lastJD = usePageStore.getState().simJD, lastAt = performance.now();
    const id = setInterval(() => {
      const el = ref.current; if (!el || !el.duration) return;
      const jd = usePageStore.getState().simJD, now = performance.now();
      const clockRate = (jd - lastJD) * 86400 / ((now - lastAt) / 1000); // simulated seconds per real second
      lastJD = jd; lastAt = now;
      const want = (jd - startJD) * 86400;
      if (want >= el.duration) { el.pause(); setDone(true); return; }
      if (want < 0) return;
      if (clockRate > 0) el.playbackRate = Math.min(16, Math.max(0.25, clockRate));
      if (Math.abs(el.currentTime - want) > 0.5) el.currentTime = want;
      if (el.paused) el.play().catch(() => {});
    }, 500);
    return () => clearInterval(id);
  }, [startJD, done]);
  // A free-running mission video holds the mission open until it ends (see endMission in the
  // store); one locked to the clock ends with the trajectory anyway. If the browser never plays
  // it (autoplay blocked, a background tab), it lets go after a generous running time; the
  // video itself is left alone.
  const holds = !restored && startJD === null;
  const [letGo, setLetGo] = useState(false);
  const letGoTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => {
    if (!holds || done || letGo) return;
    usePageStore.getState().addMissionVideo(1);
    letGoTimer.current = setTimeout(() => setLetGo(true), 20000); // until the metadata gives the length
    return () => { clearTimeout(letGoTimer.current); usePageStore.getState().addMissionVideo(-1); };
  }, [holds, done, letGo]);
  // A restored video never loads metadata, so its size arrives with the poster image.
  // Runs once per mount (onSized is an inline callback and must not retrigger it).
  const onSizedRef = useRef(onSized);
  onSizedRef.current = onSized;
  useEffect(() => {
    if (!restored) return;
    const img = new Image();
    img.onload = () => onSizedRef.current();
    img.src = poster;
  }, [restored, poster]);
  return (
    <span className={styles.videoWrap}>
    <video
      ref={ref}
      src={done ? undefined : src}
      poster={poster}
      className={styles.video}
      autoPlay={!done}
      muted={!sound}
      playsInline
      preload={done ? "none" : "auto"}
      onLoadedMetadata={(e) => {
        const el = e.currentTarget; el.playbackRate = rate; onSized();
        if (holds && !letGo) {
          clearTimeout(letGoTimer.current);
          letGoTimer.current = setTimeout(() => setLetGo(true), (el.duration / rate) * 1500 + 5000);
        }
        // If the browser refuses audio autoplay, fall back to muted rather than not playing.
        if (sound) el.play().catch(() => { el.muted = true; el.play().catch(() => {}); });
      }}
      onEnded={() => setDone(true)}
    />
    {!done && <span ref={countRef} className={styles.videoCountdown} />}
    </span>
  );
}

// `mobile`: the phone layout's terminal. Adds tappable keys for what a phone keyboard
// lacks (Tab, arrows), a 16px input so iOS doesn't zoom on focus, no autocorrect, and
// keeps the prompt in view as the cell resizes. `onFocusChange` reports the keyboard
// opening and closing (the prompt gaining and losing focus).
export default function Terminal({ mobile = false, onFocusChange }: { mobile?: boolean; onFocusChange?: (focused: boolean) => void } = {}) {
  const [lines, setLines] = useState<Line[]>([]);
  const terminalPush = usePageStore((s) => s.terminalPush);
  const transcriptPlaying = usePageStore((s) => s.transcriptPlaying); // prompt hidden while a mission transcript plays
  const handledPushSeqRef = useRef(0);
  useEffect(() => {
    if (!terminalPush || terminalPush.seq === handledPushSeqRef.current) return;
    handledPushSeqRef.current = terminalPush.seq;
    // "__IN__name" renders as an echoed command line ("> name"); everything else is output.
    setLines((prev) => [
      ...prev,
      ...terminalPush.lines.map((text) =>
        text.startsWith("__IN__")
          ? { text: `> ${text.slice(6)}`, type: "input" as const }
          : { text, type: "output" as const }
      ),
    ]);
  }, [terminalPush]);
  const [input, setInput] = useState("");
  const [cursorPos, setCursorPos] = useState(0);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  // Command history for Up/Down. `historyIndex` is where we are while browsing
  // (history.length = not browsing); `draft` is what was typed before browsing.
  const historyRef = useRef<string[]>([]);
  const historyIndexRef = useRef<number>(0);
  const draftRef = useRef<string>("");

  // Restore the transcript and command history once, then keep them saved.
  const [hydrated, setHydrated] = useState(false); // saving waits for the restore, so it can't wipe it
  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(HISTORY_KEY) ?? "null");
      // Replace, don't prepend: React dev mode runs mount effects twice.
      if (saved?.lines?.length) setLines(saved.lines.map((l: Line) => ({ ...l, restored: true })));
      if (saved?.commands?.length) { historyRef.current = saved.commands; historyIndexRef.current = saved.commands.length; }
    } catch { /* no storage, or nothing usable in it */ }
    setHydrated(true);
  }, []);
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    if (!hydrated) return;
    try {
      localStorage.setItem(HISTORY_KEY, JSON.stringify({
        lines: lines.slice(-HISTORY_LINES).map(({ text, type }) => ({ text, type })),
        commands: historyRef.current.slice(-HISTORY_COMMANDS),
      }));
    } catch { /* storage unavailable */ }
  }, [lines, hydrated]);

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
        {
          text: matches
            .map((m) => run(isCommandWord ? m : [...words.slice(0, -1), m].join(" "), m))
            .join("  "),
          type: "output",
        },
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
    if (transcriptPlaying || typingRef.current) { e.preventDefault(); return; }
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

    if (e.key === "Enter") runCommand(input);
  };

  // Run a command line, exactly as pressing Enter does: echo, history, output.
  // `preset` replaces running it, for a command whose effect already happened.
  const runCommand = (line: string, preset?: string[]) => {
    const trimmed = line.trim();
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

    const output = preset
      ? preset
      : command
      ? command.execute(args)
      : [`Unknown command: ${name}. Type "${run("help")}" for available commands.`];

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
  };

  // A clicked command: type it into the prompt, then press Enter. Clicks and keys
  // are ignored while it types. The prompt keeps focus only with a mouse, so a tap
  // on a phone doesn't open the keyboard.
  const typingRef = useRef(false);
  const typeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => () => { if (typeTimerRef.current) clearTimeout(typeTimerRef.current); }, []);
  const typeAndRun = (command: string, preset?: string[]) => {
    if (typingRef.current || transcriptPlaying) {
      // Busy: a scene request still shows up, just without the typing.
      if (preset) setLines((prev) => [...prev, { text: `> ${command}`, type: "input" }, ...preset.map((text) => ({ text, type: "output" as const }))]);
      return;
    }
    typingRef.current = true;
    if (window.matchMedia("(pointer: fine)").matches) inputRef.current?.focus();
    const step = Math.min(TYPE_MAX_STEP_MS, Math.max(TYPE_MIN_STEP_MS, TYPE_TOTAL_MS / command.length));
    let typed = 0;
    const tick = () => {
      typed++;
      setInput(command.slice(0, typed));
      setCursorPos(typed);
      if (typed < command.length) {
        typeTimerRef.current = setTimeout(tick, step);
      } else {
        typeTimerRef.current = setTimeout(() => {
          typingRef.current = false;
          runCommand(command, preset);
        }, step * 2);
      }
    };
    setInput("");
    setCursorPos(0);
    typeTimerRef.current = setTimeout(tick, step);
  };
  const r = (text: string) => rich(text, (command) => typeAndRun(command));

  // A command typed in from the scene (e.g. clicking Venus): typed and entered
  // like a clicked command, with the scene's output.
  const terminalType = usePageStore((s) => s.terminalType);
  const handledTypeSeqRef = useRef(0);
  useEffect(() => {
    if (!terminalType || terminalType.seq === handledTypeSeqRef.current) return;
    handledTypeSeqRef.current = terminalType.seq;
    typeAndRun(terminalType.command, terminalType.lines);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [terminalType]);

  const beforeCaret = input.slice(0, cursorPos);
  const afterCaret = input.slice(cursorPos);

  // Mobile: when the terminal changes size (it goes full screen, the keyboard opens),
  // keep its newest lines and the prompt in view.
  const rootRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = rootRef.current;
    if (!mobile || !el) return;
    const ro = new ResizeObserver(() => { el.scrollTop = el.scrollHeight; });
    ro.observe(el);
    return () => ro.disconnect();
  }, [mobile]);

  // Mobile keys: run help, step through history, complete. They don't take focus,
  // so an open keyboard stays open; the editing keys open it when it's closed.
  const mobileKeys: [string, string, () => void][] = [
    ["help", "Run help", () => typeAndRun("help")],
    ["↑", "Previous command", () => { browseHistory(-1); inputRef.current?.focus(); }],
    ["↓", "Next command", () => { browseHistory(1); inputRef.current?.focus(); }],
    ["tab", "Complete", () => { handleTab(); inputRef.current?.focus(); }],
  ];

  return (
    <div ref={rootRef} className={mobile ? `${styles.terminal} ${styles.mobile}` : styles.terminal} onClick={() => inputRef.current?.focus()}>
      {lines.map((line, i) =>
        line.type === "output" && line.text.startsWith("__VIDEO__") ? (
          <div key={i} className={styles.imageRow}>
            <VideoLine src={line.text.slice(9)} restored={line.restored} onSized={() => bottomRef.current?.scrollIntoView({ behavior: "smooth" })} />
          </div>
        ) : line.type === "output" && line.text.startsWith("__MODEL__") ? (
          <div key={i} className={styles.imageRow}>
            <ModelLine probe={line.text.slice(9)} restored={line.restored} onSized={() => bottomRef.current?.scrollIntoView({ behavior: "smooth" })} />
          </div>
        ) : line.type === "output" && line.text.startsWith("__IMG__") ? (
          <div key={i} className={styles.imageRow}>
            {line.text.slice(7).split(",").map((src, j) => (
              <img key={j} src={src} alt="" className={styles.poster} onLoad={() => bottomRef.current?.scrollIntoView({ behavior: "smooth" })} />
            ))}
          </div>
        ) : line.type === "output" && line.text.startsWith("__TIMED__") ? (
          <div key={i} className={styles.timedRow}>
            <span className={`${styles.timedText} ${styles.output}`}>{r(line.text.split("__TIMED__")[1])}</span>
            <span className={styles.dim}>{r(line.text.split("__TIMED__")[2])}</span>
          </div>
        ) : line.type === "output" && line.text.startsWith("__COL__") ? (
          <div key={i} className={styles.colRow}>
            <span className={`${styles.colLeft} ${styles.output}`}>{r(line.text.split("__COL__")[1])}</span>
            <span className={styles.dim}>{r(line.text.split("__COL__")[2])}</span>
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
                {r(line.text.split("__GRAY__")[0])}
                <span className={styles.gray}>{r(line.text.split("__GRAY__")[1])}</span>
              </>
            ) : line.text.includes("__SMALL__") ? (
              <>
                {r(line.text.split("__SMALL__")[0])}
                <span className={styles.small}>{r(line.text.split("__SMALL__")[1])}</span>
              </>
            ) : line.text.includes("__DIM__") ? (
              <>
                {r(line.text.split("__DIM__")[0])}
                <span className={styles.dim}>{r(line.text.split("__DIM__")[1])}</span>
              </>
            ) : (
              r(line.text)
            )}
          </div>
        )
      )}
      <div className={styles.inputRow} style={transcriptPlaying ? { display: "none" } : undefined}>
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
            onFocus={onFocusChange && (() => onFocusChange(true))}
            onBlur={onFocusChange && (() => onFocusChange(false))}
            autoFocus={!mobile} // on a phone a focused prompt opens the keyboard (and full screen)
            spellCheck={false}
            autoComplete="off"
            {...(mobile && { autoCapitalize: "off", autoCorrect: "off", enterKeyHint: "go" as const })}
          />
        </div>
      </div>
      {mobile && !transcriptPlaying && (
        <div className={styles.keys}>
          {mobileKeys.map(([label, name, action]) => (
            <button key={label} type="button" aria-label={name} className={styles.key}
              onPointerDown={(e) => e.preventDefault()} onMouseDown={(e) => e.preventDefault()}
              onClick={(e) => { e.stopPropagation(); if (!typingRef.current) action(); }}>{label}</button>
          ))}
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
