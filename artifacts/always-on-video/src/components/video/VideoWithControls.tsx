import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ChevronDown, ChevronUp, Repeat, Volume2, VolumeX } from 'lucide-react';
import VideoTemplate, { SCENE_DURATIONS } from './VideoTemplate';
import { useSceneControls } from './useSceneControls';

const PROGRESS_TICK_MS = 60;

interface ControlBarProps {
  visible: boolean;
  collapsed: boolean;
  locked: boolean;
  muted: boolean;
  sceneKeys: string[];
  activeIndex: number;
  activeDuration: number;
  tick: number;
  onToggleLock: () => void;
  onToggleMuted: () => void;
  onJumpTo: (index: number) => void;
  onToggleCollapsed: () => void;
}

function ProgressSegments({
  sceneKeys,
  activeIndex,
  activeDuration,
  tick,
  onJumpTo,
}: {
  sceneKeys: string[];
  activeIndex: number;
  activeDuration: number;
  tick: number;
  onJumpTo: (index: number) => void;
}) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    setElapsed(0);
    const start = performance.now();
    const id = window.setInterval(() => {
      setElapsed(performance.now() - start);
    }, PROGRESS_TICK_MS);
    return () => window.clearInterval(id);
  }, [tick]);

  const progress = activeDuration > 0 ? Math.min(1, elapsed / activeDuration) : 0;

  return (
    <div className="flex-1 flex items-center gap-1.5">
      {sceneKeys.map((key, i) => {
        const isActive = i === activeIndex;
        const fill = isActive ? progress * 100 : 0;
        return (
          <button
            key={key}
            onClick={() => onJumpTo(i)}
            className="flex-1 rounded-full overflow-hidden cursor-pointer transition-all relative"
            style={{
              height: '12px',
              minHeight: '12px',
              background: 'rgba(255,255,255,0.2)',
            }}
            onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.height = '16px'; (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.25)'; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.height = '12px'; (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.2)'; }}
            aria-label={`Jump to scene ${i + 1}`}
            aria-current={isActive ? 'true' : undefined}
          >
            <div
              className="absolute inset-y-0 left-0 rounded-full"
              style={{
                width: `${fill}%`,
                background: 'rgba(255,255,255,0.9)',
                transition: 'width 100ms linear',
              }}
            />
          </button>
        );
      })}
    </div>
  );
}

function ControlBar({
  visible,
  collapsed,
  locked,
  muted,
  sceneKeys,
  activeIndex,
  activeDuration,
  tick,
  onToggleLock,
  onToggleMuted,
  onJumpTo,
  onToggleCollapsed,
}: ControlBarProps) {
  return (
    <div
      className="flex items-center gap-3"
      style={{
        background: 'rgba(0,0,0,0.5)',
        backdropFilter: 'blur(8px)',
        padding: '16px 20px',
        transition: 'transform 200ms ease-out, opacity 200ms ease-out',
        transform: visible ? 'translateY(0)' : 'translateY(100%)',
        opacity: visible ? 1 : 0,
        pointerEvents: visible ? 'auto' : 'none',
      }}
      aria-hidden={!visible}
    >
      {/* Scene lock */}
      <button
        onClick={onToggleLock}
        className="flex items-center justify-center rounded-lg transition-colors"
        style={{
          width: '56px',
          height: '56px',
          color: locked ? '#ffffff' : 'rgba(255,255,255,0.6)',
          background: locked ? 'rgba(255,255,255,0.15)' : 'transparent',
          flexShrink: 0,
        }}
        title={locked ? 'Loop current scene: on' : 'Loop current scene: off'}
        aria-label={locked ? 'Loop current scene: on' : 'Loop current scene: off'}
        aria-pressed={locked}
      >
        <Repeat style={{ width: '32px', height: '32px' }} />
      </button>

      {/* Mute toggle */}
      <button
        onClick={onToggleMuted}
        className="flex items-center justify-center rounded-lg transition-colors"
        style={{
          width: '56px',
          height: '56px',
          color: muted ? 'rgba(255,255,255,0.4)' : 'rgba(255,255,255,0.8)',
          background: 'transparent',
          flexShrink: 0,
        }}
        title={muted ? 'Unmute audio' : 'Mute audio'}
        aria-label={muted ? 'Unmute audio' : 'Mute audio'}
        aria-pressed={muted}
      >
        {muted
          ? <VolumeX style={{ width: '32px', height: '32px' }} />
          : <Volume2 style={{ width: '32px', height: '32px' }} />
        }
      </button>

      {/* Divider */}
      <div style={{ width: '1px', alignSelf: 'stretch', background: 'rgba(255,255,255,0.15)' }} aria-hidden="true" />

      {/* Progress segments */}
      <ProgressSegments
        sceneKeys={sceneKeys}
        activeIndex={activeIndex}
        activeDuration={activeDuration}
        tick={tick}
        onJumpTo={onJumpTo}
      />

      {/* Scene counter */}
      <div style={{ fontSize: '20px', color: 'rgba(255,255,255,0.6)', fontFamily: 'monospace', flexShrink: 0, fontVariantNumeric: 'tabular-nums' }}>
        {activeIndex + 1}/{sceneKeys.length}
      </div>

      {/* Collapse chevron */}
      <button
        onClick={onToggleCollapsed}
        className="flex items-center justify-center rounded-lg transition-colors"
        style={{
          width: '56px',
          height: '56px',
          color: 'rgba(255,255,255,0.6)',
          background: 'transparent',
          flexShrink: 0,
        }}
        title={collapsed ? 'Show controls' : 'Hide controls'}
        aria-label={collapsed ? 'Show controls' : 'Hide controls'}
        aria-expanded={!collapsed}
      >
        {collapsed
          ? <ChevronUp style={{ width: '40px', height: '40px' }} />
          : <ChevronDown style={{ width: '40px', height: '40px' }} />
        }
      </button>
    </div>
  );
}

export default function VideoWithControls() {
  const isIframed = typeof window !== 'undefined' && window.self !== window.top;

  const {
    sceneKeys, activeIndex, locked, mountKey, tick,
    durations, activeDuration, onSceneChange, jumpTo, toggleLock,
  } = useSceneControls(SCENE_DURATIONS);

  const [muted, setMuted] = useState(true);
  const [collapsed, setCollapsed] = useState(false);
  const [hovering, setHovering] = useState(false);
  const [tapPinned, setTapPinned] = useState(false);
  const sensorRef = useRef<HTMLDivElement | null>(null);

  const handlePointerEnter = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    if (e.pointerType === 'mouse') setHovering(true);
  }, []);
  const handlePointerLeave = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    if (e.pointerType === 'mouse') setHovering(false);
  }, []);
  const handlePointerDown = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    if (e.pointerType === 'mouse') return;
    if (collapsed) setTapPinned(true);
  }, [collapsed]);
  const handleToggleCollapsed = useCallback(() => {
    setCollapsed((c) => {
      if (!c) { setHovering(false); setTapPinned(false); }
      return !c;
    });
  }, []);

  useEffect(() => {
    if (!(collapsed && tapPinned)) return;
    const onDocPointerDown = (e: PointerEvent) => {
      if (e.pointerType === 'mouse') return;
      const sensor = sensorRef.current;
      if (sensor && !sensor.contains(e.target as Node)) setTapPinned(false);
    };
    document.addEventListener('pointerdown', onDocPointerDown);
    return () => document.removeEventListener('pointerdown', onDocPointerDown);
  }, [collapsed, tapPinned]);

  const barVisible = !collapsed || hovering || tapPinned;

  // Export path: no props, recording lifecycle intact
  if (!isIframed) return <VideoTemplate />;

  return (
    <div className="relative w-full h-screen">
      <VideoTemplate
        key={mountKey}
        durations={durations}
        loop
        muted={muted}
        onSceneChange={onSceneChange}
      />

      {/* Bottom sensor + control bar */}
      <div
        ref={sensorRef}
        className="absolute bottom-0 left-0 right-0 flex flex-col justify-end"
        style={{ height: '25%', zIndex: 100 }}
        onPointerEnter={handlePointerEnter}
        onPointerLeave={handlePointerLeave}
        onPointerDown={handlePointerDown}
      >
        <div className="flex-1 w-full" aria-hidden="true" />
        <ControlBar
          visible={barVisible}
          collapsed={collapsed}
          locked={locked}
          muted={muted}
          sceneKeys={sceneKeys}
          activeIndex={activeIndex}
          activeDuration={activeDuration}
          tick={tick}
          onToggleLock={toggleLock}
          onToggleMuted={() => setMuted((m) => !m)}
          onJumpTo={jumpTo}
          onToggleCollapsed={handleToggleCollapsed}
        />
      </div>
    </div>
  );
}
