"use client";

import dynamic from 'next/dynamic';
import Image from 'next/image';

const Globe = dynamic(() => import('@/components/Globe').then(mod => mod.ThreeJSGlobeWithDots), {
  ssr: false,
});

export default function Home() {
  return (
    <div style={{ 
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: 'center', 
      justifyContent: 'center', 
      minHeight: '100vh', 
      gap: '2rem', 
      padding: '2rem' 
    }}>
      <h1 style={{ 
        fontFamily: 'var(--font-roboto-mono)', 
        fontSize: '3.75rem', 
        letterSpacing: '-0.025em' 
      }}>
        DAVID VAN VLIET
      </h1>
      <Globe size={600} />
      <a 
        href="https://www.radar.ltd" 
        target="_blank" 
        rel="noopener noreferrer"
        style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '0.75rem', 
          transition: 'opacity 0.3s' 
        }}
        onMouseEnter={(e) => e.currentTarget.style.opacity = '0.7'}
        onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
      >
        <Image 
          src="/thenewlogo.png" 
          alt="Radar" 
          width={40} 
          height={40}
        />
        <span style={{ 
          fontFamily: 'Roboto Mono, sans-serif', 
          fontSize: '1.5rem',
          fontWeight: '600'
        }}>
          Radar
        </span>
      </a>
    </div>
  );
}
