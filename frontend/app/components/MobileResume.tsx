"use client";

import styles from "./MobileResume.module.css";

function Section({ title }: { title: string }) {
  return <div className={styles.section}>{title}</div>;
}

function Entry({
  title,
  right,
  sub,
  subRight,
  bullets,
}: {
  title: string;
  right?: string;
  sub?: string;
  subRight?: string;
  bullets?: string[];
}) {
  return (
    <div className={styles.entry}>
      <div className={styles.entryHeader}>
        <span className={styles.entryTitle}>{title}</span>
        {right && <span className={styles.entryRight}>{right}</span>}
      </div>
      {(sub || subRight) && (
        <div className={styles.entryHeader}>
          {sub && <span className={styles.entrySub}>{sub}</span>}
          {subRight && <span className={styles.entryRight}>{subRight}</span>}
        </div>
      )}
      {bullets?.map((b, i) => (
        <div key={i} className={styles.bullet}>{b}</div>
      ))}
    </div>
  );
}

export default function MobileResume() {
  return (
    <div className={styles.resume}>

      <Section title="EDUCATION" />
      <Entry
        title="RICE UNIVERSITY (2022-2025)"
        right="Houston, Texas"
        sub="Major in Computer Science (BA); Minor in Statistics"
        subRight="May 2025"
        bullets={[
          "Coursework: Quantitative Risk Management, Stochastic Models, Market Models, AI & Cybernetics, Linear Algebra, Multivariable Calculus, Differential Equations",
        ]}
      />

      <Section title="WORK EXPERIENCE" />
      <Entry
        title="RADAR CORPORATION"
        right="San Francisco, CA"
        sub="Founder"
        subRight="Jun 2025 - Present"
        bullets={[
          "• Founded Radar to build information platforms that facilitate optimal capital flow for VC and PE firms.",
          "• Radar offers rich data on millions of companies, a cutting edge agentic search method, and agentic monitoring of company data and news.",
          "• Single-handedly developed Radar through various pilots to make it a competitive, SOTA solution in its market.",
        ]}
      />
      <Entry
        title="MAIN CAPITAL PARTNERS"
        right="The Hague, NL"
        sub="Software Engineering"
        subRight="May 2023 - Jul 2024"
        bullets={[
          "• Built an OCR application in Python that processes PDF files into a standardized database-ready format.",
          "• Built a multi-label classification model that predicts a company's sector from its website text.",
          "• Built a t-SNE application that ranks all companies in the database by similarity to an input company.",
        ]}
      />

      <Section title="PROJECTS" />
      <Entry title="INTRINSIC" right="Jan 2026" bullets={["• Agentic fundamental analysis through a spreadsheet workspace using verified SEC data."]} />
      <Entry title="PIXELPOLISH" right="Jun 2025" bullets={["• AI-powered web interface manipulation platform for real-time DOM editing via natural language."]} />
      <Entry title="DYNASTAI (3rd place Hackathon)" right="May 2025" bullets={["• Adaptive reinforcement learning environment for medieval kingdom management."]} />
      <Entry title="DYNAMIC DELTA HEDGING SIMULATION" right="Dec 2024" bullets={["• Delta hedging strategy for options on natural gas and crude oil futures using Black-Scholes and GBM."]} />
      <Entry title="OPTIONS IV SURFACE GENERATOR" right="Feb 2025" bullets={["• 3D implied volatility surface generator from a stock ticker input."]} />
      <Entry title="DISCORD-LIKE MESSAGING BOARD" right="Dec 2024" bullets={["• Messaging board with workspaces, channels, and reactions built in TypeScript."]} />

      <Section title="ADDITIONAL" />
      <div className={styles.text}>Skills: Advanced in Python, Postgres, Typescript, NextJS, Docker; Proficient in R, Java, Go, Excel</div>
      <div className={styles.text}>Languages: Fluent in English, Dutch; Intermediate in Italian, Japanese</div>
      <div className={styles.text}>Interests: Chess, rock climbing, reading, hiking</div>

    </div>
  );
}
