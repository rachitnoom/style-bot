import React from 'react';
import { motion } from 'framer-motion';

export default function Scene2() {
  return (
    <motion.div 
      className="absolute inset-0 flex flex-col items-center justify-center"
      initial={{ scale: 0.8, opacity: 0, rotateX: 45 }}
      animate={{ scale: 1, opacity: 1, rotateX: 0 }}
      exit={{ 
        scale: 1.2, 
        opacity: 0,
        filter: "blur(10px)",
        transition: { duration: 0.8, ease: "easeIn" } 
      }}
      transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
    >
      
      {/* Central Core Concept */}
      <div className="relative w-[40vw] h-[40vw] flex items-center justify-center">
        
        {/* Rotating Rings */}
        {[1, 2, 3].map((ring, i) => (
          <motion.div
            key={ring}
            className={`absolute rounded-full border border-primary/30 ${i === 1 ? 'border-secondary/40 border-dashed' : ''}`}
            style={{ width: `${100 - (i * 20)}%`, height: `${100 - (i * 20)}%` }}
            animate={{ rotate: i % 2 === 0 ? 360 : -360 }}
            transition={{ duration: 15 + (i * 5), repeat: Infinity, ease: "linear" }}
          />
        ))}

        {/* Data points */}
        {Array.from({ length: 8 }).map((_, i) => (
          <motion.div
            key={`dot-${i}`}
            className="absolute w-2 h-2 rounded-full bg-secondary box-glow-cyan"
            style={{
              top: '50%', left: '50%',
              transformOrigin: `0 ${15 + (i%3)*5}vw`,
              transform: `rotate(${i * 45}deg) translateY(-${15 + (i%3)*5}vw)`
            }}
            animate={{ opacity: [0.2, 1, 0.2] }}
            transition={{ duration: 1.5 + (i * 0.2), repeat: Infinity, delay: i * 0.1 }}
          />
        ))}

        <div className="absolute z-30 text-center">
          <motion.div
            className="font-mono text-primary text-[1vw] mb-4 tracking-widest"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 1 }}
          >
            CONSTANT FLOW
          </motion.div>
          <motion.h2 
            className="text-[8vw] font-bold leading-none tracking-tighter text-white uppercase text-glow-cyan"
            initial={{ scale: 0.5, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: "spring", stiffness: 100, damping: 20, delay: 1.2 }}
          >
            100%
          </motion.h2>
          <motion.div
            className="font-display text-secondary text-[2vw] font-bold mt-2"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 1.5 }}
          >
            UPTIME
          </motion.div>
        </div>
      </div>

    </motion.div>
  );
}