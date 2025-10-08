"use client";

import dynamic from 'next/dynamic';
import Image from 'next/image';
import { useEffect, useState } from 'react';

const Globe = dynamic(() => import('@/components/Globe').then(mod => mod.ThreeJSGlobeWithDots), {
  ssr: false,
});

export default function Home() {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

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
        fontSize: isMobile ? '1.5rem' : '2.5rem', 
        letterSpacing: '-0.025em',
        textAlign: 'center'
      }}>
        DAVID VAN VLIET
      </h1>
      <Globe size={isMobile ? 350 : 600} />
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
          Radar
        </span>
      </a>
    </div>
  );
}
