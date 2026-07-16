import React, { useEffect, useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useVideoPlayer } from '@/lib/video/hooks';

import Scene0 from './video_scenes/Scene0';
import Scene1 from './video_scenes/Scene1';
import Scene2 from './video_scenes/Scene2';
import Scene3 from './video_scenes/Scene3';
import Scene4 from './video_scenes/Scene4';

export const SCENE_DURATIONS: Record<string, number> = {
  scene0: 6000,
  scene1: 7000,
  scene2: 7000,
  scene3: 7000,
  scene4: 6000,
};

const SCENE_COMPONENTS: Record<string, React.ComponentType> = {
  scene0: Scene0,
  scene1: Scene1,
  scene2: Scene2,
  scene3: Scene3,
  scene4: Scene4,
};

const SCENE_START_SEC: Record<string, number> = (() => {
  const out: Record<string, number> = {};
  let cumulativeMs = 0;
  for (const [key, ms] of Object.entries(SCENE_DURATIONS)) {
    out[key] = cumulativeMs / 1000;
    cumulativeMs += ms;
  }
  return out;
})();

const AUDIO_SEEK_EPSILON_SEC = 0.18;

export default function VideoTemplate({
  durations = SCENE_DURATIONS,
  loop = true,
  muted = false,
  onSceneChange,
}: {
  durations?: Record<string, number>;
  loop?: boolean;
  muted?: boolean;
  onSceneChange?: (sceneKey: string) => void;
} = {}) {
  const { currentSceneKey } = useVideoPlayer({ durations, loop });
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    onSceneChange?.(currentSceneKey);
  }, [currentSceneKey, onSceneChange]);

  const baseSceneKey = currentSceneKey.replace(/_r[12]$/, '');
  const sceneIndex = Object.keys(SCENE_DURATIONS).indexOf(baseSceneKey);
  const SceneComponent = SCENE_COMPONENTS[baseSceneKey];

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.volume = 0.45;
    const targetTime = SCENE_START_SEC[baseSceneKey] ?? 0;
    if (Math.abs(audio.currentTime - targetTime) > AUDIO_SEEK_EPSILON_SEC) {
      audio.currentTime = targetTime;
    }
    audio.play().catch(() => {});
  }, [currentSceneKey, baseSceneKey, muted]);

  return (
    <div className="relative w-full h-screen bg-black overflow-hidden flex items-center justify-center font-display">

      {/* PERSISTENT BACKGROUND LAYER */}
      <div className="absolute inset-0 z-0">
        <motion.div
          className="absolute inset-0"
          style={{ background: 'radial-gradient(circle at center, #050510, #000000)' }}
          animate={{ scale: [1, 1.2, 1], opacity: [0.8, 1, 0.8] }}
          transition={{ duration: 10, repeat: Infinity, ease: 'linear' }}
        />

        {/* Persistent video backgrounds with crossfading */}
        <motion.video
          src={`${import.meta.env.BASE_URL}videos/data-tunnel.mp4`}
          className="absolute inset-0 w-full h-full object-cover"
          style={{ mixBlendMode: 'screen' }}
          autoPlay
          muted
          loop
          playsInline
          animate={{
            opacity: (sceneIndex === 1 || sceneIndex === 4) ? 0.6 : 0,
            scale: sceneIndex === 1 ? 1.05 : 1.1,
          }}
          transition={{ duration: 2, ease: 'easeInOut' }}
        />

        <motion.video
          src={`${import.meta.env.BASE_URL}videos/energy-core.mp4`}
          className="absolute inset-0 w-full h-full object-cover"
          style={{ mixBlendMode: 'screen' }}
          autoPlay
          muted
          loop
          playsInline
          animate={{
            opacity: (sceneIndex === 2 || sceneIndex === 4) ? 0.8 : 0,
            scale: sceneIndex === 2 ? 1 : 1.1,
          }}
          transition={{ duration: 2, ease: 'easeInOut' }}
        />
      </div>

      {/* PERSISTENT MIDGROUND — status HUD */}
      <motion.div
        className="absolute top-[5vh] left-[5vw] z-40 font-mono text-xs tracking-widest uppercase flex flex-col gap-1"
        style={{ color: '#00F0FF' }}
        animate={{
          opacity: sceneIndex === 0 ? 0 : 1,
          y: sceneIndex === 0 ? -20 : 0,
        }}
        transition={{ duration: 1 }}
      >
        <span className="flex items-center gap-2">
          <motion.div
            className="w-2 h-2 rounded-full"
            style={{ background: '#FF0055' }}
            animate={{ opacity: [1, 0.2, 1] }}
            transition={{ duration: 1, repeat: Infinity }}
          />
          SYS.VIGILANT // ALWAYS_ON
        </span>
        <span style={{ color: 'rgba(255,255,255,0.5)' }}>UPTIME: 99.999%</span>
      </motion.div>

      {/* PERSISTENT MIDGROUND — scanning line */}
      <motion.div
        className="absolute left-0 right-0 z-30"
        style={{ height: '2px', background: 'rgba(0,240,255,0.2)', filter: 'blur(1px)' }}
        animate={{ top: ['-10%', '110%'] }}
        transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
      />

      {/* FOREGROUND SCENES */}
      <div className="absolute inset-0 z-20">
        <AnimatePresence mode="popLayout">
          {SceneComponent && <SceneComponent key={currentSceneKey} />}
        </AnimatePresence>
      </div>

      {/* Noise overlay */}
      <div className="noise-overlay" />

      {/* Vignette */}
      <div
        className="absolute inset-0 z-50 pointer-events-none"
        style={{ background: 'radial-gradient(circle at center, transparent 40%, rgba(0,0,0,0.8) 100%)' }}
      />

      {/* Audio */}
      <audio
        ref={audioRef}
        src={`${import.meta.env.BASE_URL}audio/bg_music.mp3`}
        preload="auto"
        autoPlay
        muted={muted}
      />
    </div>
  );
}
