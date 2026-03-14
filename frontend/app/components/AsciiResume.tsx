"use client";

import styles from "./AsciiResume.module.css";

export default function AsciiResume() {
  return (
    <div className={styles.resume}>
      <div className={styles.inner}>
      <div className={styles.separator}>══════════════════════════════════════════════════════════════════</div>
      <div className={styles.sectionTitle}>EDUCATION</div>
      <div className={styles.separator}>══════════════════════════════════════════════════════════════════</div>

      <div className={styles.spacer} />
      <div className={styles.row}>
        <span>RICE UNIVERSITY (2022-2025)</span>
        <span>Houston, TX</span>
      </div>
      <div className={styles.row}>
        <span>Major in Computer Science (BA); Minor in Statistics</span>
        <span>May 2025 (Graduated 1 year early)</span>
      </div>
      <div className={styles.spacer} />
      <div className={styles.text}>Coursework: Quantitative Risk Management, Stochastic Models, Market Models,</div>
      <div className={styles.text}>AI &amp; Cybernetics, Linear Algebra, Multivariable Calculus, Differential Equations</div>

      <div className={styles.spacer} />
      <div className={styles.separator}>══════════════════════════════════════════════════════════════════</div>
      <div className={styles.sectionTitle}>WORK EXPERIENCE</div>
      <div className={styles.separator}>══════════════════════════════════════════════════════════════════</div>

      <div className={styles.spacer} />
      <div className={styles.row}>
        <span>RADAR CORPORATION</span>
        <span>San Francisco, California</span>
      </div>
      <div className={styles.row}>
        <span>Founder</span>
        <span>Jun 2025 - Present</span>
      </div>
      <div className={styles.subSeparator}>──────────────────────────────────────────────────────────────────</div>
      <div className={styles.text}>• Founded Radar to build information platforms that facilitate optimal capital flow for VC and PE firms.</div>
      <div className={styles.text}>• Radar offers rich data on millions of companies, a cutting edge agentic search method, and agentic monitoring of company data and news.</div>
      <div className={styles.text}>• Single-handedly developed Radar through various pilots to make it a competitive, SOTA solution in its market, and am now deploying the product at enterprise scale.</div>

      <div className={styles.spacer} />
      <div className={styles.row}>
        <span>MAIN CAPITAL PARTNERS</span>
        <span>The Hague, The Netherlands</span>
      </div>
      <div className={styles.row}>
        <span>Software Engineering</span>
        <span>May 2023 - Jul 2023, May 2024 - Jul 2024</span>
      </div>
      <div className={styles.subSeparator}>──────────────────────────────────────────────────────────────────</div>
      <div className={styles.text}>• Built an application using OCR in Python that processes PDF files into a standardized format, ready to upload to a database.</div>
      <div className={styles.text}>• Built a multi-label classification model in Python that takes the text on a company{"'"}s website using Beautiful Soup and predicts its sector.</div>
      <div className={styles.text}>• Built an application using t-SNE that takes a company and returns a ranking of all companies in the database, ranked by their similarity to the input company.</div>

      <div className={styles.spacer} />
      <div className={styles.separator}>══════════════════════════════════════════════════════════════════</div>
      <div className={styles.sectionTitle}>PROJECTS</div>
      <div className={styles.separator}>══════════════════════════════════════════════════════════════════</div>

      <div className={styles.spacer} />
      <div className={styles.row}>
        <span>INTRINSIC</span>
        <span>Jan 2026</span>
      </div>
      <div className={styles.text}>• Agentic fundamental analysis through a spreadsheet workspace, where agents use verified SEC data on any publicly listed company to automate financial modeling.</div>

      <div className={styles.spacer} />
      <div className={styles.row}>
        <span>PIXELPOLISH</span>
        <span>Jun 2025</span>
      </div>
      <div className={styles.text}>• AI-powered web interface manipulation platform enabling real-time DOM editing and natural language CSS/HTML modifications via OpenAI and Claude model integrations.</div>

      <div className={styles.spacer} />
      <div className={styles.row}>
        <span>DYNASTAI (3rd place Hackathon winner)</span>
        <span>May 2025</span>
      </div>
      <div className={styles.text}>• Adaptive reinforcement learning environment for medieval kingdom management, featuring a dynamic reward system that evolves based on agent behavior.</div>

      <div className={styles.spacer} />
      <div className={styles.row}>
        <span>DYNAMIC DELTA HEDGING SIMULATION</span>
        <span>Dec 2024</span>
      </div>
      <div className={styles.text}>• Delta hedging strategy simulation for options on natural gas and crude oil futures using Black-Scholes, Geometric Brownian Motion simulation and payoff functions.</div>

      <div className={styles.spacer} />
      <div className={styles.row}>
        <span>OPTIONS IMPLIED VOLATILITY SURFACE GENERATOR</span>
        <span>Feb 2025</span>
      </div>
      <div className={styles.text}>• 3D IV Surface generator that takes a stock ticker as input. Strike price on x-axis, DTE on y-axis, and IV on z-axis.</div>

      <div className={styles.spacer} />
      <div className={styles.row}>
        <span>DISCORD-LIKE MESSAGING BOARD</span>
        <span>Dec 2024</span>
      </div>
      <div className={styles.text}>• Messaging board similar to Discord built in Typescript. Allows for the creation of workspaces that contain channels wherein users can post and react.</div>

      <div className={styles.spacer} />
      <div className={styles.separator}>══════════════════════════════════════════════════════════════════</div>
      <div className={styles.sectionTitle}>ADDITIONAL</div>
      <div className={styles.separator}>══════════════════════════════════════════════════════════════════</div>

      <div className={styles.spacer} />
      <div className={styles.text}>Skills: Advanced in Python, Postgres, Typescript, NextJS, Docker;</div>
      <div className={styles.text}>Proficient in R, Java, Go, Excel; Limited experience with C, C++, Ruby</div>
      <div className={styles.spacer} />
      <div className={styles.text}>Languages: Fluent in English, Dutch; Intermediate in Italian, Japanese</div>
      <div className={styles.spacer} />
      <div className={styles.text}>Interests: Chess, rock climbing, reading, hiking</div>
      </div>
    </div>
  );
}
