"use client";

import dynamic from 'next/dynamic';
import Image from 'next/image';
import { useEffect, useState } from 'react';

const Globe = dynamic(() => import('@/components/Globe').then(mod => mod.ThreeJSGlobeWithDots), {
  ssr: false,
});

export default function Home() {
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
    { id: 1, lat: 52.3676, lon: 4.9041, color: '#00ff00', size: 2, info: 'Amsterdam — Birthplace\n(2004-2022)' },
    { id: 2, lat: 35.682839, lon: 139.759455, color: '#00ff00', size: 2, info: 'Tokyo - Favorite city\n(every now and then)' },
    { id: 3, lat: 29.7604, lon: -95.3698, color: '#00ff00', size: 2, info: 'Houston - Rice University\n(2022-2025)' },
    { id: 4, lat: 37.4419, lon: -122.1430, color: '#00ff00', size: 2, info: 'Palo Alto — Best city in the world, current location\n(2025-present)' },
  ];

  return (
    <div style={{ 
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: 'center', 
      justifyContent: 'center', 
      minHeight: '100vh', 
      gap: isMobile ? '1rem' : '2rem', 
      padding: isMobile ? '1rem' : '2rem' 
    }}>
      <h1 style={{ 
        fontFamily: 'var(--font-roboto-mono)', 
        fontSize: isMobile ? '1rem' : '1.5rem', 
        letterSpacing: '-0.025em',
        textAlign: 'center'
      }}>
        David van Vliet
      </h1>
      <p style={{
        fontFamily: 'var(--font-roboto-mono)',
        fontSize: isMobile ? '0.75rem' : '0.875rem',
        textAlign: 'center',
        color: '#ededed',
        marginTop: '-1rem'
      }}>
        21; Palo Alto, CA; david@marketradar.co
      </p>
      <div style={{ position: 'relative' }}>
        <Globe size={isMobile ? 350 : 600} dots={dots} onDotClick={setSelectedDot} />
        {selectedDot && (
          <div style={{
            position: 'absolute',
            left: isMobile ? 'calc(350px + 1rem)' : 'calc(600px + 1rem)',
            top: '50%',
            transform: 'translateY(-50%)',
            background: 'rgba(0, 0, 0, 0.8)',
            color: '#ededed',
            padding: '1rem',
            borderRadius: '8px',
            fontFamily: 'var(--font-roboto-mono)',
            fontSize: isMobile ? '0.75rem' : '0.875rem',
            minWidth: '300px',
            whiteSpace: 'pre-line'
          }}>
            {selectedDot.info}
          </div>
        )}
      </div>
      <a 
        href="https://www.radar.ltd" 
        target="_blank" 
        rel="noopener noreferrer"
        style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '0.5rem', 
          transition: 'opacity 0.3s' 
        }}
        onMouseEnter={(e) => e.currentTarget.style.opacity = '0.7'}
        onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
      >
        <Image 
          src="/0a0a0a_logo.png" 
          alt="Radar" 
          width={isMobile ? 30 : 40} 
          height={isMobile ? 30 : 40}
        />
        <span style={{ 
          fontFamily: 'Roboto Mono, sans-serif', 
          fontSize: isMobile ? '1.125rem' : '1.5rem',
          fontWeight: '600'
        }}>
          radar
        </span>
      </a>
    </div>
  );
}
