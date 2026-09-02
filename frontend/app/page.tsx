"use client";

import dynamic from 'next/dynamic';
import React, { useEffect, useState } from 'react';
import Image from 'next/image';
import ChessBoard from './components/ChessBoard';
import Navbar from './components/Navbar';
import MobilePage from './components/MobilePage';
import Terminal from './components/Terminal';
import AsciiResume from './components/AsciiResume';
import BlogPost from './components/BlogPost';
import styles from './page.module.css';
import { usePageStore } from './store/pageStore';
import { BODY_FACTS } from './components/solarSystemData';

const SolarSystem = dynamic(() => import('./components/SolarSystem').then(mod => mod.SolarSystem), {
  ssr: false,
});

export default function GridPage() {
  const [isMobile, setIsMobile] = useState(false);
  const [selectedDot, setSelectedDot] = useState<any>(null);
  const [hoveredDot, setHoveredDot] = useState<any>(null);
  const [hoveredBody, setHoveredBody] = useState<string | null>(null);
  const [focusedBody, setFocusedBody] = useState<string | null>("Earth");
  const leftPanel = usePageStore((s) => s.leftPanel);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const dots = [
    { id: 1, lat: 52.3676, lon: 4.9041, color: '#00ff00', size: 4, label: 'Amsterdam', subtitle: '2004-2022', description: 'Born here' },
    { id: 3, lat: 29.7604, lon: -95.3698, color: '#00ff00', size: 4, label: 'Houston', subtitle: '2022-2025', description: 'Rice University' },
    { id: 4, lat: 37.4419, lon: -122.1430, color: '#00ff00', size: 4, label: 'San Francisco', subtitle: '2025', description: 'Radar' },
    { id: 5, lat: 40.7128, lon: -74.0060, color: '#00ff00', size: 4, label: 'New York City', subtitle: '2026-present', description: 'Based here' },
  ];

  if (isMobile) return <MobilePage />;

  return (
    <>
      <Navbar />
      <div className={styles.gridContainer}>
      {/* Two identical cells - each half width */}
      <div className={styles.cell2}>
          {leftPanel === "resume" ? (
            <AsciiResume />
          ) : leftPanel === "blog" ? (
            <BlogPost />
          ) : (
            <div className={styles.globeWrapper}>
              <div className={styles.globeLabel}>
                {hoveredDot ? (
                  <div className={styles.globeLabelRow}><span className={styles.globeLabelLocation}>{hoveredDot.label}</span><span className={styles.globeLabelSubtitle}>{hoveredDot.subtitle}</span><span className={styles.globeLabelDescription}>{hoveredDot.description}</span></div>
                ) : hoveredBody ? (
                  <div className={styles.globeLabelRow}><span className={styles.globeLabelLocation}>{hoveredBody}</span><span className={styles.globeLabelDescription}>Click to focus</span></div>
                ) : focusedBody ? (
                  <>
                    <span className={styles.globeLabelLocation}>{focusedBody}</span>
                    {BODY_FACTS[focusedBody] && <span className={styles.globeLabelFact}>{BODY_FACTS[focusedBody]}</span>}
                  </>
                ) : null}
              </div>
              <div className={styles.globeCanvas}>
                <SolarSystem dots={dots} onDotClick={setSelectedDot} onDotHover={setHoveredDot} onBodyHover={setHoveredBody} onFocusChange={setFocusedBody} dotSizeMultiplier={0.3} />
              </div>
            </div>
          )}
      </div>
      
      <div className={styles.rightCell}>
        <div className={styles.cell3}>
          <Terminal />
        </div>
        <div className={styles.linksSection}>
          <div className={styles.linksContainer}>
            <div className={styles.linksTop}>
              <div className={styles.cell6}>
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
              <div className={styles.linksTopRight}>
                <div className={styles.cell7}>
                  <Image 
                    src="/pulsar-map.png" 
                    alt="Pulsar Map" 
                    width={2000} 
                    height={2000}
                    className={styles.pulsarMap}
                  />
                </div>
                <div className={styles.linksTopRightBottom}>
                  <div className={styles.cell8}>
                    <Image 
                      src="/orbital-2-1-0.png" 
                      alt="Orbital Visualization" 
                      width={1000} 
                      height={1000}
                      className={styles.orbitalImage}
                    />
                  </div>
                  <div className={styles.cell9}>
                    <Image 
                      src="/monolith.jpg" 
                      alt="2001: A Space Odyssey Monolith" 
                      width={1200} 
                      height={545}
                      className={styles.monolithImage}
                    />
                  </div>
                </div>
              </div>
            </div>
            <div className={styles.cell5}>
              <a href="https://tryradar.ai" target="_blank" rel="noopener noreferrer">
                <Image 
                  src="/radar-full-logo.png" 
                  alt="Radar Logo" 
                  width={150} 
                  height={150}
                  className={styles.radarLogo}
                />
              </a>
            </div>
          </div>
          <div className={styles.cell4}>
            <ChessBoard />
          </div>
        </div>
      </div>
    </div>
    </>
  );
}

