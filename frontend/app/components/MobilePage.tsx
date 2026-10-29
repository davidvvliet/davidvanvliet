"use client";

import React, { useEffect, useRef, useState } from 'react';
import dynamic from 'next/dynamic';
import Navbar from './Navbar';
import Terminal from './Terminal';
import PhotoGrid from './PhotoGrid';
import type { Photo } from '../photoTypes';
import styles from './MobilePage.module.css';
import labelStyles from '../page.module.css'; // the desktop label overlay, reused
import { usePageStore } from '../store/pageStore';
import { BODY_FACTS } from './solarSystemData';
import { MISSIONS } from '../missions';

const SolarSystem = dynamic(() => import('./SolarSystem').then(mod => mod.SolarSystem), {
  ssr: false,
});
const GoldenRecord = dynamic(() => import('./GoldenRecord'), { ssr: false });

const dots = [
  { id: 1, lat: 52.3676, lon: 4.9041, color: '#00ff00', size: 4, label: 'Amsterdam', subtitle: '2004-2022', description: 'Born here' },
  { id: 3, lat: 29.7604, lon: -95.3698, color: '#00ff00', size: 4, label: 'Houston', subtitle: '2022-2025', description: 'Rice University' },
  { id: 4, lat: 37.4419, lon: -122.1430, color: '#00ff00', size: 4, label: 'San Francisco', subtitle: '2025', description: 'Worked on Radar Corp' },
  { id: 5, lat: 40.7128, lon: -74.0060, color: '#00ff00', size: 4, label: 'New York City', subtitle: '2026-present', description: 'Based here' },
];
type Dot = (typeof dots)[number];

// `panel`: a non-explore view (resume, a post) for the top cell; null shows the solar system.
export default function MobilePage({ panel, photos }: { panel: React.ReactNode; photos: Photo[] }) {
  // Labels on touch: no hover, so a tapped dot, a tapped star, and the focused body.
  const [tappedDot, setTappedDot] = useState<Dot | null>(null);
  const [tappedStar, setTappedStar] = useState<{ name: string; lightYears: number; spectral?: string; fact?: string } | null>(null);
  const [focusedBody, setFocusedBody] = useState<string | null>('Sun');
  const missionId = usePageStore((s) => s.trackRequest?.id ?? null);
  const simJD = usePageStore((s) => s.simJD);
  const missionFormat = MISSIONS.find((m) => m.id === missionId)?.dateFormat ?? 'month';
  const missionDate = missionId && simJD
    ? new Date((simJD - 2440587.5) * 86400000).toLocaleDateString('en-US',
        missionFormat === 'day'
          ? { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' }
          : { month: 'long', year: 'numeric', timeZone: 'UTC' })
    : null;

  // The terminal fills the screen while its keyboard is open, sized to the visible
  // viewport so the prompt sits just above the keyboard. Leaving the prompt (keyboard
  // closed, a tap outside, or ×) shrinks it back after a beat, so a tap that keeps
  // the focus inside doesn't flicker it.
  const [termFull, setTermFull] = useState(false);
  const [viewport, setViewport] = useState<{ top: number; height: number } | null>(null);
  const blurTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onTermFocus = (focused: boolean) => {
    if (blurTimer.current) clearTimeout(blurTimer.current);
    if (focused) setTermFull(true);
    else blurTimer.current = setTimeout(() => setTermFull(false), 150);
  };
  useEffect(() => () => { if (blurTimer.current) clearTimeout(blurTimer.current); }, []);
  useEffect(() => {
    const vv = window.visualViewport;
    if (!termFull || !vv) return;
    const fit = () => setViewport({ top: vv.offsetTop, height: vv.height });
    fit();
    vv.addEventListener('resize', fit);
    vv.addEventListener('scroll', fit);
    return () => { vv.removeEventListener('resize', fit); vv.removeEventListener('scroll', fit); };
  }, [termFull]);

  return (
    <>
      <Navbar />
      <div className={styles.container}>

        {/* Top 61.8%: controlled by terminal */}
        <div className={styles.globeCell}>
          {panel ? (
            panel
          ) : (
            <div className={labelStyles.globeWrapper}>
              <div className={labelStyles.globeLabel}>
                {tappedDot ? (
                  <div className={labelStyles.globeLabelRow}><span className={labelStyles.globeLabelLocation}>{tappedDot.label}</span><span className={labelStyles.globeLabelSubtitle}>{tappedDot.subtitle}</span><span className={labelStyles.globeLabelDescription}>{tappedDot.description}</span></div>
                ) : tappedStar ? (
                  <>
                    <div className={labelStyles.globeLabelRow}><span className={labelStyles.globeLabelLocation}>{tappedStar.name}</span><span className={labelStyles.globeLabelDescription}>{tappedStar.lightYears.toLocaleString()} light-years</span>{tappedStar.spectral && <span className={labelStyles.globeLabelSubtitle}>Type {tappedStar.spectral}</span>}</div>
                    {tappedStar.fact && <span className={labelStyles.globeLabelFact}>{tappedStar.fact}</span>}
                  </>
                ) : focusedBody ? (
                  <>
                    <span className={labelStyles.globeLabelLocation}>{focusedBody}</span>
                    {BODY_FACTS[focusedBody] && <span className={labelStyles.globeLabelFact}>{BODY_FACTS[focusedBody]}</span>}
                  </>
                ) : null}
                {missionDate && <span className={labelStyles.missionDate}>{missionDate}</span>}
              </div>
              <div className={labelStyles.globeCanvas}>
                <SolarSystem
                  dots={dots}
                  onDotClick={(d) => { setTappedDot(d as Dot); setTappedStar(null); }}
                  onStarHover={(star) => { setTappedStar(star); if (star) setTappedDot(null); }}
                  onFocusChange={(name) => { setFocusedBody(name); setTappedDot(null); }}
                  dotSizeMultiplier={0.3}
                />
              </div>
            </div>
          )}
        </div>

        {/* Bottom 38.2%: terminal | links+radar */}
        <div className={styles.bottomCell}>

          {/* Left 61.8%: terminal */}
          <div
            className={termFull ? `${styles.terminalCell} ${styles.terminalFull}` : styles.terminalCell}
            style={termFull && viewport ? { top: viewport.top, height: viewport.height } : undefined}
          >
            <Terminal mobile onFocusChange={onTermFocus} />
            {termFull && (
              <button type="button" className={styles.terminalClose} aria-label="Close terminal"
                onClick={() => (document.activeElement as HTMLElement | null)?.blur()}>×</button>
            )}
          </div>

          {/* Right 38.2%: links + record top (38.2%) | photos bottom (61.8%) */}
          <div className={styles.rightCell}>

            {/* Top 38.2%: links left (38.2%) | golden record right (61.8%) */}
            <div className={styles.linksContainer}>
              <div className={styles.linksCell}>
                <a href="https://github.com/davidvvliet" target="_blank" rel="noopener noreferrer" className={styles.link}>
                  github
                </a>
                <a href="https://www.linkedin.com/in/davidvvliet/" target="_blank" rel="noopener noreferrer" className={styles.link}>
                  linkedin
                </a>
                <a href="https://x.com/deepfieldnorth" target="_blank" rel="noopener noreferrer" className={styles.link}>
                  X
                </a>
              </div>
              <div className={styles.recordCell}>
                <GoldenRecord fitWidth />
              </div>
            </div>

            {/* Bottom 61.8%: photos */}
            <div className={styles.photosCell}>
              <PhotoGrid photos={photos} />
            </div>

          </div>
        </div>

      </div>
    </>
  );
}
