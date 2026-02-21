"use client";

import dynamic from 'next/dynamic';
import React, { useEffect, useState } from 'react';
import Image from 'next/image';
import ChessBoard from './components/ChessBoard';
import Navbar from './components/Navbar';
import MobilePage from './components/MobilePage';
import styles from './page.module.css';

const Globe = dynamic(() => import('./components/Globe').then(mod => mod.ThreeJSGlobeWithDots), {
  ssr: false,
});

export default function GridPage() {
  const [isMobile, setIsMobile] = useState(false);
  const [selectedDot, setSelectedDot] = useState<any>(null);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const dots = [
    { id: 1, lat: 52.3676, lon: 4.9041, color: '#00ff00', size: 4 },
    { id: 2, lat: 35.682839, lon: 139.759455, color: '#00ff00', size: 4 },
    { id: 3, lat: 29.7604, lon: -95.3698, color: '#00ff00', size: 4 },
    { id: 4, lat: 37.4419, lon: -122.1430, color: '#00ff00', size: 4 },
  ];

  if (isMobile) return <MobilePage />;

  return (
    <>
      <Navbar />
      <div className={styles.gridContainer}>
      {/* Two identical cells - each half width */}
      <div className={styles.cell2}>
          <Globe size={isMobile ? 300 : 500} dots={dots} onDotClick={setSelectedDot} dotSizeMultiplier={0.3} />
      </div>
      
      <div className={styles.rightCell}>
        <div className={styles.cell3}>
          <div>
            Based in Palo Alto, building <a href="https://theradarcorp.com" target="_blank" rel="noopener noreferrer" className={styles.descriptionLink}>Radar Corp.</a>
            <br /><br />
            We make products for private and public market investors to facilitate optimal capital flow.
          </div>
          <br />
          <br />
          <div>
            
          </div>
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

