"use client";

import dynamic from 'next/dynamic';

const Globe = dynamic(() => import('@/components/Globe').then(mod => mod.ThreeJSGlobeWithDots), {
  ssr: false,
});

export default function Home() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen gap-8 p-8">
      <h1 className="font-[family-name:var(--font-roboto-mono)] text-4xl sm:text-6xl md:text-7xl tracking-tight">
        DAVID VAN VLIET
      </h1>
      <Globe size={600} />
    </div>
  );
}
