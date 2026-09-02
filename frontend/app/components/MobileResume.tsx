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
        right="Houston, TX"
        sub="Major in Computer Science (BA); Minor in Statistics"
        subRight="May 2025"
        bullets={[
          "Additional Relevant Coursework: Quantitative Risk Management; Stochastic Models; Market Models; Foundational Artificial Intelligence & Cybernetics; Linear Algebra; Multivariable Calculus; Differential Equations",
        ]}
      />

      <Section title="WORK EXPERIENCE" />
      <Entry
        title="WHYAI TECHNOLOGIES, INC."
        right="New York, NY"
        sub="Chief Technology Officer"
        subRight="May 2026 - Aug 2026"
        bullets={[
          "• Grew revenue from $0 to $40K ARR, with software adopted by 75 enterprise users (40 daily active).",
          "• Raised a six-figure funding round.",
          "• Led a team of 4 spanning engineering and go-to-market as CTO.",
          "• Owned and managed enterprise-grade infrastructure across AWS Bedrock and Azure.",
        ]}
      />
      <Entry
        title="RADAR AI"
        right="San Francisco, CA"
        sub="Founder"
        subRight="Mar 2025 - May 2025"
        bullets={[
          "• Founded and built Radar entirely solo, an AI-powered market intelligence platform for VC and PE, now deployed at enterprise scale. Built on Next.js, Python, Exa, PostgreSQL, Qdrant.",
          "• Created a rich database of millions of companies and people, continuously updated through automated scraping pipelines.",
          "• Engineered a cutting-edge search layer using LLMs and vector search to surface the most relevant results for any investment mandate.",
          "• Built an automated monitoring engine that surfaces relevant developments to customers using rich firm context.",
        ]}
      />
      <Entry
        title="MAIN CAPITAL PARTNERS"
        right="The Hague, NL"
        sub="Software Engineering"
        subRight="May 2023 - Jul 2023, May 2024 - Jul 2024"
        bullets={[
          "• Built a Python OCR application that converts PDFs into a standardized, database-ready format, eliminating manual data entry.",
          "• Built a multi-label classification model that predicts company sectors from scraped website text, improving filtering and fixing misclassifications in their database.",
          "• Built a t-SNE-based similarity engine that ranks all database companies against an input company, accelerating analysts' search for acquisition targets.",
        ]}
      />

      <Section title="PROJECTS" />
      <Entry title="INTRINSIC" right="Jan 2026" bullets={["• Agentic fundamental analysis through a spreadsheet workspace, where agents use verified SEC data on any publicly listed company to automate financial modeling. Built a web-based sheets engine from scratch."]} />
      <Entry title="PIXELPOLISH" right="Jun 2025" bullets={["• AI-powered web interface manipulation platform enabling real-time DOM editing and natural language CSS/HTML modifications. Design your frontend without coding, agents do it for you."]} />
      <Entry title="DYNASTAI (Hackathon winner)" right="May 2025" bullets={["• Adaptive reinforcement learning environment for medieval kingdom management, with a dynamic reward system that evolves based on how the player plays."]} />
      <Entry title="OPTIONS IV SURFACE GENERATOR" right="Feb 2025" bullets={["• 3D IV surface generator from a stock ticker: strike on x, DTE on y, IV on z. Configurable option type, strike range, and strike vs. moneyness."]} />

      <Section title="ADDITIONAL" />
      <div className={styles.text}>Technical Skills: Experienced with Python, Next.js, TypeScript, PostgreSQL, Docker; Intermediate in R, Java, Go, Excel; Limited experience with C, C++, Ruby</div>
      <div className={styles.text}>Languages: Fluent in English, Dutch; Intermediate in Italian, Japanese</div>
      <div className={styles.text}>Hobbies & Interests: Chess, rock climbing, reading, hiking</div>

    </div>
  );
}
