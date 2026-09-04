import React from 'react';
import { motion } from 'framer-motion';
import logoImg from '../assets/logo.jpg';

export default function AnimatedLogo({ size = 38, showText = true }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      {/* Logo image with animated ring */}
      <motion.div
        style={{
          position: 'relative',
          width: size,
          height: size,
          flexShrink: 0,
        }}
        whileHover={{ scale: 1.1 }}
        transition={{ type: 'spring', stiffness: 400, damping: 15 }}
      >
        {/* Rotating glow ring */}
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 6, repeat: Infinity, ease: 'linear' }}
          style={{
            position: 'absolute',
            inset: -3,
            borderRadius: '50%',
            background: 'conic-gradient(from 0deg, #5b8def, #a855f7, #06b6d4, #5b8def)',
            zIndex: 0,
            filter: 'blur(2px)',
            opacity: 0.8,
          }}
        />
        {/* Inner mask */}
        <div
          style={{
            position: 'absolute',
            inset: 1,
            borderRadius: '50%',
            background: '#06090f',
            zIndex: 1,
          }}
        />
        {/* Logo */}
        <motion.img
          src={logoImg}
          alt="MuleNet"
          animate={{ filter: ['brightness(1)', 'brightness(1.15)', 'brightness(1)'] }}
          transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
          style={{
            position: 'absolute',
            inset: 2,
            width: size - 4,
            height: size - 4,
            borderRadius: '50%',
            objectFit: 'cover',
            zIndex: 2,
          }}
        />
      </motion.div>

      {showText && (
        <motion.div
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2, duration: 0.5 }}
        >
          <div style={{
            fontSize: 15,
            fontWeight: 800,
            letterSpacing: '-0.5px',
            background: 'linear-gradient(90deg, #ffffff, #5b8def, #a855f7)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
            lineHeight: 1.2,
          }}>
            MuleNet
          </div>
          <div style={{
            fontSize: 8,
            fontWeight: 700,
            letterSpacing: '2px',
            textTransform: 'uppercase',
            color: 'var(--text-muted)',
            marginTop: 1,
          }}>
            Fraud Intelligence
          </div>
        </motion.div>
      )}
    </div>
  );
}
