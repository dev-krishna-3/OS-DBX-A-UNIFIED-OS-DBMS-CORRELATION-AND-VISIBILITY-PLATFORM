import { lazy, Suspense } from 'react';
import { MotionConfig } from 'framer-motion';
import { Hero } from './components/Hero';
import { Lab } from './components/Lab';

const How = lazy(() => import('./components/How'));
const Trust = lazy(() => import('./components/Trust'));
const LabsCarousel = lazy(() => import('./components/LabsCarousel'));
const Faq = lazy(() => import('./components/Faq'));
const Footer = lazy(() => import('./components/Footer'));

export default function App() {
  return (
    <MotionConfig reducedMotion="user">
      <a href="#lab" className="sr-only focus:not-sr-only focus:absolute focus:left-3 focus:top-3 focus:z-50 focus:rounded-full focus:bg-white focus:px-4 focus:py-2">Skip to the lab</a>
      <main>
        <Hero />
        <Lab />
        <Suspense fallback={<div className="min-h-[900px]" />}>
          <How /><Trust /><LabsCarousel /><Faq />
        </Suspense>
      </main>
      <Suspense fallback={null}><Footer /></Suspense>
    </MotionConfig>
  );
}
