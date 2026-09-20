import React, { useState } from 'react';
import { Check, Copy } from 'lucide-react';
import { useToast } from './Toast';

/**
 * CopyHash — Displays Bitcoin addresses, hashes, txids with one-click copy.
 */
export default function CopyHash({
  value = '',
  truncate = true,
  truncateLength = 8,
  showLabel = false,
  label = '',
  className = '',
}) {
  const [copied, setCopied] = useState(false);
  const toast = useToast();

  if (!value) return <span className="text-dim font-mono text-xs">—</span>;

  const displayValue = truncate && value.length > truncateLength * 2 + 3
    ? `${value.slice(0, truncateLength)}...${value.slice(-truncateLength)}`
    : value;

  const handleCopy = async (e) => {
    e.stopPropagation();
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(value);
      } else {
        // Fallback for non-https / older browsers
        const textarea = document.createElement('textarea');
        textarea.value = value;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
      }
      setCopied(true);
      if (toast && toast.showToast) {
        toast.showToast(`Copied ${label || 'value'} to clipboard`, 'info');
      }
      setTimeout(() => setCopied(false), 1800);
    } catch (err) {
      console.error('Failed to copy', err);
    }
  };

  return (
    <span
      className={`inline-flex items-center gap-1 font-mono text-xs cursor-pointer group ${className}`}
      onClick={handleCopy}
      title={`Click to copy: ${value}`}
      style={{
        padding: '2px 6px',
        borderRadius: '4px',
        backgroundColor: 'rgba(255, 255, 255, 0.03)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        transition: 'background-color 0.15s, border-color 0.15s',
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.backgroundColor = 'rgba(0, 240, 255, 0.06)';
        e.currentTarget.style.borderColor = 'rgba(0, 240, 255, 0.25)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.03)';
        e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.08)';
      }}
    >
      <span style={{ color: 'var(--text-main, #f1f5f9)' }}>{displayValue}</span>
      <button
        type="button"
        style={{
          background: 'none',
          border: 'none',
          padding: 0,
          cursor: 'pointer',
          color: copied ? 'var(--risk-low, #10b981)' : 'var(--text-dim, #64748b)',
          display: 'flex',
          alignItems: 'center',
        }}
        aria-label="Copy to clipboard"
      >
        {copied ? (
          <Check size={12} color="#10b981" />
        ) : (
          <Copy size={12} className="opacity-60 group-hover:opacity-100" />
        )}
      </button>
    </span>
  );
}
