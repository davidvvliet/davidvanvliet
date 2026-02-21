"use client";

import React from 'react';
import dynamic from 'next/dynamic';
import Image from 'next/image';
import Navbar from './Navbar';
import styles from './MobilePage.module.css';

const Globe = dynamic(() => import('./Globe').then(mod => mod.ThreeJSGlobeWithDots), {
  ssr: false,
});

const dots = [
  { id: 1, lat: 52.3676, lon: 4.9041, color: '#00ff00', size: 4 },
  { id: 2, lat: 35.682839, lon: 139.759455, color: '#00ff00', size: 4 },
  { id: 3, lat: 29.7604, lon: -95.3698, color: '#00ff00', size: 4 },
  { id: 4, lat: 37.4419, lon: -122.1430, color: '#00ff00', size: 4 },
];

export default function MobilePage() {
  return (
    <>
      <Navbar />
      <div className={styles.container}>

        {/* Top 61.8%: Globe */}
        <div className={styles.globeCell}>
          <Globe size={320} dots={dots} onDotClick={() => {}} dotSizeMultiplier={0.3} />
        </div>

        {/* Bottom 38.2%: bio | links+radar */}
        <div className={styles.bottomCell}>

          {/* Left 61.8%: bio text */}
          <div className={styles.bioCell}>
            Based in Palo Alto, building{' '}
            <a href="https://theradarcorp.com" target="_blank" rel="noopener noreferrer" className={styles.descriptionLink}>
              Radar Corp.
            </a>
            <br />
            We make products for private and public market investors to facilitate optimal capital flow.
          </div>

          {/* Right 38.2%: links top | radar bottom */}
          <div className={styles.rightCell}>

            {/* Top 61.8%: links */}
            <div className={styles.linksCell}>
              <a href="https://github.com/davidvvliet" target="_blank" rel="noopener noreferrer" className={styles.link}>
                github
              </a>
              <a href="https://www.linkedin.com/in/davidvvliet/" target="_blank" rel="noopener noreferrer" className={styles.link}>
                linkedin
              </a>
            </div>

            {/* Bottom 38.2%: radar logo */}
            <div className={styles.radarCell}>
              <a href="https://tryradar.ai" target="_blank" rel="noopener noreferrer">
                <Image
                  src="/radar-full-logo.png"
                  alt="Radar Logo"
                  width={100}
                  height={100}
                  className={styles.radarLogo}
                />
              </a>
            </div>

          </div>
        </div>

      </div>
    </>
  );
}
