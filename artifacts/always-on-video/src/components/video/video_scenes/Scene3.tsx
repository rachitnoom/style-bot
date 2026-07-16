import React from 'react';
import { motion } from 'framer-motion';

export default function Scene3() {
  const stats = [
    { label: "LATENCY", value: "<1MS", x: "-20vw", y: "-15vh", delay: 0.5 },
    { label: "THROUGHPUT", value: "99.9T", x: "20vw", y: "-20vh", delay: 0.8 },
    { label: "REDUNDANCY", value: "N+2", x: "-25vw", y: "15vh", delay: 1.1 },
    { label: "INTEGRITY", value: "100%", x: "20vw", y: "20vh", delay: 1.4 },
  ];

  return (
    <motion.div 
      className="absolute inset-0 flex items-center justify-center overflow-hidden"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ 
        clipPath: "circle(0% at 50% 50%)",
        transition: { duration: 1, ease: [0.76, 0, 0.24, 1] } 
      }}
    >
      {/* Dynamic Grid Background specific to this scene */}
      <motion.div 
        className="absolute inset-0 bg-[linear-gradient(to_right,#00f0ff11_1px,transparent_1px),linear-gradient(to_bottom,#00f0ff11_1px,transparent_1px)]"
        style={{ backgroundSize: '4vw 4vw' }}
        initial={{ opacity: 0, scale: 2 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 2, ease: "easeOut" }}
      />

      {/* Floating Stat Cards */}
      {stats.map((stat, i) => (
        <motion.div
          key={i}
          className="absolute glass-panel border border-primary/30 p-[2vw] min-w-[15vw]"
          initial={{ opacity: 0, x: 0, y: 0, scale: 0 }}
          animate={{ opacity: 1, x: stat.x, y: stat.y, scale: 1 }}
          transition={{ type: "spring", stiffness: 50, damping: 15, delay: stat.delay }}
        >
          <div className="font-mono text-secondary text-[1vw] mb-2">{stat.label}</div>
          <div className="font-display text-white text-[3vw] font-bold leading-none">{stat.value}</div>
          <motion.div 
            className="h-[2px] bg-primary mt-4 w-full origin-left"
            initial={{ scaleX: 0 }}
            animate={{ scaleX: 1 }}
            transition={{ duration: 1, delay: stat.delay + 0.5 }}
          />
        </motion.div>
      ))}

      {/* Center Title */}
      <div className="relative z-30 text-center bg-background/80 p-8 backdrop-blur-md border border-white/10">
        <motion.h2 
          className="text-[6vw] font-bold text-white uppercase tracking-tighter"
          initial={{ clipPath: "inset(50% 0 50% 0)" }}
          animate={{ clipPath: "inset(0% 0 0% 0)" }}
          transition={{ duration: 1, delay: 2, ease: [0.16, 1, 0.3, 1] }}
        >
          Relentless
        </motion.h2>
        <motion.p
          className="text-primary font-mono text-[1.5vw] tracking-widest mt-2"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1, delay: 2.5 }}
        >
          MOMENTUM
        </motion.p>
      </div>

    </motion.div>
  );
}