import React from 'react';
import { motion } from 'framer-motion';

export default function Scene0() {
  return (
    <motion.div 
      className="absolute inset-0 flex items-center justify-center"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ 
        opacity: 0,
        scale: 1.5,
        filter: 'blur(20px)',
        transition: { duration: 1.2, ease: [0.16, 1, 0.3, 1] } 
      }}
    >
      {/* Intro Grid */}
      <motion.div 
        className="absolute inset-0 perspective-grid opacity-20"
        initial={{ opacity: 0 }}
        animate={{ opacity: 0.2 }}
        transition={{ duration: 3, delay: 0.5 }}
      />

      <div className="relative z-10 flex flex-col items-center justify-center">
        
        {/* Pre-title */}
        <div className="overflow-hidden mb-4">
          <motion.div
            className="font-mono text-primary text-[1.5vw] tracking-[0.5em] uppercase"
            initial={{ y: "100%", opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.8, delay: 1, ease: [0.16, 1, 0.3, 1] }}
          >
            Initiating Sequence
          </motion.div>
        </div>

        {/* Main Title */}
        <div className="relative">
          {/* Glitch layers */}
          {['cyan', 'magenta'].map((color, i) => (
            <motion.h1
              key={color}
              className={`absolute top-0 left-0 text-[12vw] font-bold tracking-tighter uppercase ${color === 'cyan' ? 'text-primary mix-blend-screen' : 'text-secondary mix-blend-screen'}`}
              initial={{ opacity: 0, x: 0 }}
              animate={{ 
                opacity: [0, 0, 1, 0, 1, 1],
                x: i === 0 ? [-10, 5, -5, 0] : [10, -5, 5, 0]
              }}
              transition={{ 
                duration: 0.5, 
                delay: 2 + (i * 0.1),
                times: [0, 0.1, 0.2, 0.3, 0.4, 1]
              }}
            >
              Always On
            </motion.h1>
          ))}
          
          <motion.h1 
            className="text-[12vw] font-bold tracking-tighter uppercase text-white relative z-10"
            initial={{ opacity: 0, scale: 0.9, filter: 'blur(10px)' }}
            animate={{ opacity: 1, scale: 1, filter: 'blur(0px)' }}
            transition={{ duration: 1.5, delay: 1.5, ease: "easeOut" }}
          >
            Always On
          </motion.h1>
        </div>

        {/* Subtitle */}
        <motion.div 
          className="mt-8 flex items-center gap-6"
          initial={{ opacity: 0, width: 0 }}
          animate={{ opacity: 1, width: "auto" }}
          transition={{ duration: 1, delay: 3, ease: "anticipate" }}
        >
          <div className="h-[1px] w-[10vw] bg-gradient-to-r from-transparent to-primary" />
          <p className="font-mono text-white/70 text-[1.2vw] tracking-widest uppercase">
            No Sleep. No Pause.
          </p>
          <div className="h-[1px] w-[10vw] bg-gradient-to-l from-transparent to-primary" />
        </motion.div>

      </div>
    </motion.div>
  );
}