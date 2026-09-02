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
        <span className={styles.bold}>RICE UNIVERSITY (2022-2025)</span>
        <span className={styles.right}>Houston, Texas</span>
      </div>
      <div className={styles.row}>
        <span className={styles.sub}>Major in Computer Science (BA); Minor in Statistics</span>
        <span className={styles.right}>May 2025 (Graduated 1 year early)</span>
      </div>
      <div className={styles.spacer} />
      <div className={styles.text}>Additional Relevant Coursework: Quantitative Risk Management; Stochastic Models; Market Models;</div>
      <div className={styles.text}>Foundational Artificial Intelligence &amp; Cybernetics; Linear Algebra; Multivariable Calculus; Differential Equations</div>

      <div className={styles.spacer} />
      <div className={styles.separator}>══════════════════════════════════════════════════════════════════</div>
      <div className={styles.sectionTitle}>WORK EXPERIENCE</div>
      <div className={styles.separator}>══════════════════════════════════════════════════════════════════</div>

      <div className={styles.spacer} />
      <div className={styles.row}>
        <span className={styles.bold}>WHYAI TECHNOLOGIES, INC. (<a href="https://yaihq.com" target="_blank" rel="noopener noreferrer">yAIhq.com</a>)</span>
        <span className={styles.right}>New York, New York</span>
      </div>
      <div className={styles.row}>
        <span className={styles.sub}>Chief Technology Officer</span>
        <span className={styles.right}>May 2026 - Aug 2026</span>
      </div>
      <div className={styles.text}>• Grew revenue from $0 to $40K ARR, with software adopted by 75 enterprise users (40 daily active).</div>
      <div className={styles.text}>• Raised a six-figure funding round.</div>
      <div className={styles.text}>• Led a team of 4 spanning engineering and go-to-market as CTO.</div>
      <div className={styles.text}>• Owned and managed enterprise-grade infrastructure across AWS Bedrock and Azure.</div>

      <div className={styles.spacer} />
      <div className={styles.row}>
        <span className={styles.bold}>RADAR AI (<a href="https://tryradar.ai" target="_blank" rel="noopener noreferrer">TryRadar.ai</a>)</span>
        <span className={styles.right}>San Francisco, California</span>
      </div>
      <div className={styles.row}>
        <span className={styles.sub}>Founder</span>
        <span className={styles.right}>Mar 2025 - May 2025</span>
      </div>
      <div className={styles.text}>• Founded and built Radar entirely solo, an AI-powered market intelligence platform for VC and PE, now deployed at enterprise scale. Built on Next.js, Python, Exa, PostgreSQL, Qdrant.</div>
      <div className={styles.text}>• Created a rich database of millions of companies and people, continuously updated through automated scraping pipelines.</div>
      <div className={styles.text}>• Engineered a cutting-edge search layer using LLMs and vector search to surface the most relevant results for any investment mandate.</div>
      <div className={styles.text}>• Built an automated monitoring engine that surfaces relevant developments to customers using rich firm context (investment thesis, portfolio, preferred stages, etc.).</div>

      <div className={styles.spacer} />
      <div className={styles.row}>
        <span className={styles.bold}>MAIN CAPITAL PARTNERS (leading private equity firm in Europe)</span>
        <span className={styles.right}>The Hague, The Netherlands</span>
      </div>
      <div className={styles.row}>
        <span className={styles.sub}>Software Engineering</span>
        <span className={styles.right}>May 2023 - Jul 2023, May 2024 - Jul 2024</span>
      </div>
      <div className={styles.text}>• Built a Python OCR application that converts PDFs into a standardized, database-ready format, eliminating manual data entry.</div>
      <div className={styles.text}>• Built a multi-label classification model that predicts company sectors from scraped website text, improving filtering and fixing misclassifications in their database.</div>
      <div className={styles.text}>• Built a t-SNE-based similarity engine that ranks all database companies against an input company, accelerating analysts{"'"} search for acquisition targets.</div>

      <div className={styles.spacer} />
      <div className={styles.separator}>══════════════════════════════════════════════════════════════════</div>
      <div className={styles.sectionTitle}>PROJECTS</div>
      <div className={styles.separator}>══════════════════════════════════════════════════════════════════</div>

      <div className={styles.spacer} />
      <div className={styles.row}>
        <span className={styles.bold}>INTRINSIC (<a href="https://runintrinsic.com" target="_blank" rel="noopener noreferrer">RunIntrinsic.com</a> | <a href="https://github.com/davidvvliet/intrinsic" target="_blank" rel="noopener noreferrer">GitHub</a>)</span>
        <span className={styles.right}>Jan 2026</span>
      </div>
      <div className={styles.text}>• Agentic fundamental analysis through a spreadsheet workspace, where agents use verified SEC data on any publicly listed company to automate financial modeling. Built a web-based sheets engine from scratch. Rapidly unlocks intrinsic value and guides fundamental investors.</div>

      <div className={styles.spacer} />
      <div className={styles.row}>
        <span className={styles.bold}>PIXELPOLISH (<a href="https://github.com/davidvvliet/PixelPolish" target="_blank" rel="noopener noreferrer">GitHub</a>)</span>
        <span className={styles.right}>Jun 2025</span>
      </div>
      <div className={styles.text}>• AI-powered web interface manipulation platform enabling real-time DOM editing and natural language CSS/HTML modifications. Allows users to design their frontend without having to code, agents will do it for them.</div>

      <div className={styles.spacer} />
      <div className={styles.row}>
        <span className={styles.bold}>DYNASTAI (Hackathon winner; <a href="https://github.com/NousResearch/atropos/pull/81" target="_blank" rel="noopener noreferrer">GitHub</a>)</span>
        <span className={styles.right}>May 2025</span>
      </div>
      <div className={styles.text}>• Adaptive reinforcement learning environment for medieval kingdom management, featuring a dynamic reward system that evolves based on how the player plays the game.</div>

      <div className={styles.spacer} />
      <div className={styles.row}>
        <span className={styles.bold}>OPTIONS IMPLIED VOLATILITY SURFACE GENERATOR</span>
        <span className={styles.right}>Feb 2025</span>
      </div>
      <div className={styles.text}>• 3D IV Surface generator that takes a stock ticker as input. The graph has strike price on the x-axis, DTE on the y-axis, and IV on the z-axis. Allows for configuration of the option type, a minimum &amp; maximum strike, and if strike or moneyness is on the x-axis.</div>

      <div className={styles.spacer} />
      <div className={styles.separator}>══════════════════════════════════════════════════════════════════</div>
      <div className={styles.sectionTitle}>ADDITIONAL</div>
      <div className={styles.separator}>══════════════════════════════════════════════════════════════════</div>

      <div className={styles.spacer} />
      <div className={styles.text}>Technical Skills: Experienced with Python, Next.js, TypeScript, PostgreSQL, Docker;</div>
      <div className={styles.text}>Intermediate in R, Java, Go, Excel; Limited experience with C, C++, Ruby</div>
      <div className={styles.spacer} />
      <div className={styles.text}>Languages: Fluent in English, Dutch; Intermediate in Italian, Japanese</div>
      <div className={styles.spacer} />
      <div className={styles.text}>Hobbies &amp; Interests: Chess, rock climbing, reading, hiking</div>
      </div>
    </div>
  );
}
