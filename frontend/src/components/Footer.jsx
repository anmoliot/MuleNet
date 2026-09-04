import React from 'react';
import { motion } from 'framer-motion';

export default function Footer() {
  const year = new Date().getFullYear();

  return (
    <motion.footer
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.5, duration: 0.6, ease: 'easeOut' }}
      style={{
        position: 'relative',
        padding: '14px 24px',
        borderTop: '1px solid rgba(91, 141, 239, 0.1)',
        background: 'rgba(6, 9, 15, 0.95)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 8,
        zIndex: 10,
        flexShrink: 0,
      }}
    >
      {/* Gradient top-border glow */}
      <div style={{
        position: 'absolute',
        top: -1,
        left: '10%',
        right: '10%',
        height: 1,
        background: 'linear-gradient(90deg, transparent, rgba(91,141,239,0.5), rgba(168,85,247,0.4), transparent)',
        pointerEvents: 'none',
      }} />

      {/* Left — copyright */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <motion.div
          animate={{ opacity: [0.6, 1, 0.6] }}
          transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
          style={{
            width: 6, height: 6, borderRadius: '50%',
            background: 'linear-gradient(135deg, #5b8def, #a855f7)',
            boxShadow: '0 0 8px rgba(91,141,239,0.7)',
          }}
        />
        <span style={{
          fontSize: 11,
          color: 'var(--text-secondary)',
          fontFamily: 'Inter, system-ui, sans-serif',
        }}>
          © {year}{' '}
          <span style={{ color: '#7eb3ff', fontWeight: 600 }}>MuleNet Intelligence</span>
          {' '}— All rights reserved.
        </span>
      </div>

      {/* Center — version badge */}
      <div style={{
        fontSize: 9,
        fontWeight: 700,
        letterSpacing: '1.5px',
        textTransform: 'uppercase',
        color: 'var(--text-muted)',
        display: 'flex',
        alignItems: 'center',
        gap: 6,
      }}>
        <span style={{
          background: 'rgba(91,141,239,0.1)',
          border: '1px solid rgba(91,141,239,0.2)',
          borderRadius: 4,
          padding: '2px 7px',
          color: '#5b8def',
        }}>v1.0</span>
        Fraud Detection Platform
      </div>

      {/* Right — links */}
      <div style={{ display: 'flex', gap: 16 }}>
        {['Privacy Policy', 'Terms of Use', 'Security'].map((label) => (
          <motion.a
            key={label}
            href="#"
            whileHover={{ color: '#5b8def' }}
            style={{
              fontSize: 11,
              color: 'var(--text-secondary)',
              textDecoration: 'none',
              fontFamily: 'Inter, system-ui, sans-serif',
              transition: 'color 0.2s',
            }}
          >
            {label}
          </motion.a>
        ))}
      </div>
    </motion.footer>
  );
}
