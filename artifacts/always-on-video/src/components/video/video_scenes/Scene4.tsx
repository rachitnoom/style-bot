import React from 'react';
import { motion } from 'framer-motion';

export default function Scene4() {
  return (
    <motion.div 
      className="absolute inset-0 flex items-center justify-center bg-black"
      initial={{ clipPath: "circle(0% at 50% 50%)" }}
      animate={{ clipPath: "circle(150% at 50% 50%)" }}
      exit={{ 
        opacity: 0,
        transition: { duration: 1, ease: "easeInOut" } 
      }}
      transition={{ duration: 1.5, ease: [0.76, 0, 0.24, 1] }}
    >
      
      {/* High impact final scene */}
      
      {/* Central Light Burst */}
      <motion.div 
        className="absolute w-[80vw] h-[80vw] rounded-full bg-primary/20 blur-[100px] mix-blend-screen"
        initial={{ scale: 0, opacity: 0 }}
        animate={{ scale: 1, opacity: 0.8 }}
        transition={{ duration: 2, ease: "easeOut" }}
      />
      
      <motion.div 
        className="absolute w-[40vw] h-[40vw] rounded-full bg-secondary/30 blur-[60px] mix-blend-screen"
        initial={{ scale: 0, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 2, delay: 0.5, ease: "easeOut" }}
      />

      <div className="relative z-20 text-center flex flex-col items-center">
        
        {/* Outro Text */}
        <motion.h1 
          className="text-[12vw] font-bold text-white uppercase tracking-tighter leading-none"
          initial={{ y: 50, opacity: 0, scale: 0.9 }}
          animate={{ y: 0, opacity: 1, scale: 1 }}
          transition={{ duration: 1, delay: 1, ease: [0.16, 1, 0.3, 1] }}
        >
          Always
        </motion.h1>
        <motion.h1 
          className="text-[12vw] font-bold text-transparent bg-clip-text bg-gradient-to-r from-primary to-secondary uppercase tracking-tighter leading-none mt-[-2vw]"
          initial={{ y: 50, opacity: 0, scale: 0.9 }}
          animate={{ y: 0, opacity: 1, scale: 1 }}
          transition={{ duration: 1, delay: 1.2, ease: [0.16, 1, 0.3, 1] }}
        >
          Ready
        </motion.h1>

        {/* Lockup / Logo placeholder */}
        <motion.div 
          className="mt-12 flex items-center gap-4 border border-white/20 px-8 py-4 rounded-full glass-panel"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 2.5 }}
        >
          <div className="w-4 h-4 rounded-full bg-primary animate-pulse box-glow-cyan" />
          <span className="font-mono text-white tracking-[0.3em] text-[1.2vw]">SYSTEM ONLINE</span>
        </motion.div>

      </div>

    </motion.div>
  );
}