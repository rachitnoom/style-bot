import React from 'react';
import { motion } from 'framer-motion';

export default function Scene1() {
  const words = "THE WORLD DOES NOT STOP.".split(" ");

  return (
    <motion.div 
      className="absolute inset-0 flex items-center justify-start pl-[10vw]"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ 
        x: "-20vw", 
        opacity: 0,
        transition: { duration: 0.8, ease: [0.32, 0, 0.67, 0] } 
      }}
    >
      
      {/* Decorative HUD Elements */}
      <motion.div 
        className="absolute right-[10vw] top-[30vh] w-[40vw] h-[40vh] border border-primary/20 glass-panel flex items-center justify-center overflow-hidden"
        initial={{ clipPath: "polygon(0 50%, 100% 50%, 100% 50%, 0 50%)", opacity: 0 }}
        animate={{ clipPath: "polygon(0 0, 100% 0, 100% 100%, 0 100%)", opacity: 1 }}
        transition={{ duration: 1.5, delay: 0.5, ease: [0.16, 1, 0.3, 1] }}
      >
        <motion.div 
          className="absolute inset-0 border-[2px] border-secondary/30 scale-90"
          animate={{ rotate: 360 }}
          transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
        />
        <motion.div 
          className="text-primary font-mono text-[8vw] opacity-20"
          animate={{ scale: [1, 1.1, 1], opacity: [0.1, 0.3, 0.1] }}
          transition={{ duration: 4, repeat: Infinity }}
        >
          24/7
        </motion.div>
      </motion.div>

      <div className="relative z-20 w-[50vw]">
        {/* Staggered Text */}
        <div className="flex flex-wrap gap-[2vw]">
          {words.map((word, i) => (
            <div key={i} className="overflow-hidden">
              <motion.h2
                className="text-[6vw] font-bold leading-none tracking-tight text-white"
                initial={{ y: "100%", rotateX: -90, opacity: 0 }}
                animate={{ y: 0, rotateX: 0, opacity: 1 }}
                transition={{ 
                  duration: 0.8, 
                  delay: 0.2 + (i * 0.15),
                  ease: [0.16, 1, 0.3, 1] 
                }}
              >
                {word}
              </motion.h2>
            </div>
          ))}
        </div>

        <motion.div 
          className="mt-8 overflow-hidden"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1, delay: 1.5 }}
        >
          <motion.p 
            className="text-[2vw] font-mono text-primary max-w-lg"
            initial={{ x: -50 }}
            animate={{ x: 0 }}
            transition={{ duration: 1, delay: 1.5, ease: "easeOut" }}
          >
            NEITHER DO WE.
          </motion.p>
          <motion.div 
            className="h-1 bg-secondary mt-4 w-0 box-glow-cyan"
            animate={{ width: "100%" }}
            transition={{ duration: 2, delay: 2, ease: "easeInOut" }}
          />
        </motion.div>

      </div>
    </motion.div>
  );
}