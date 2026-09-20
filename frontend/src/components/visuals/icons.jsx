import React from 'react';

/**
 * ChainSentinel Custom Forensic SVG Iconography
 * Air-gapped, zero CDN, domain-accurate Bitcoin forensic visual language.
 */

// 1. Primary ChainSentinel Brand Logo (Interlocking shield link with forensic focal eye)
export const ChainSentinelLogo = ({ size = 32, className = '', glow = true, ...props }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 32 32"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className={className}
    {...props}
  >
    <defs>
      <linearGradient id="cs-shield-grad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#00f2fe" />
        <stop offset="100%" stopColor="#3b82f6" />
      </linearGradient>
      <linearGradient id="cs-core-grad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#f7931a" />
        <stop offset="100%" stopColor="#e28014" />
      </linearGradient>
      {glow && (
        <filter id="cs-glow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="1.5" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
      )}
    </defs>
    {/* Outer Interlocking Shield Perimeter */}
    <path
      d="M16 2.5L27 6.5V14.5C27 21.5 22.5 27.5 16 29.5C9.5 27.5 5 21.5 5 14.5V6.5L16 2.5Z"
      stroke="url(#cs-shield-grad)"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      filter={glow ? "url(#cs-glow)" : undefined}
    />
    {/* Internal Hexagonal Chain Link Node */}
    <path
      d="M16 7L22 10.5V17.5L16 21L10 17.5V10.5L16 7Z"
      stroke="#00f2fe"
      strokeWidth="1.4"
      strokeOpacity="0.75"
      fill="rgba(0, 242, 254, 0.08)"
    />
    {/* Central Bitcoin Forensic Crosshair Eye */}
    <circle cx="16" cy="14" r="3.5" stroke="url(#cs-core-grad)" strokeWidth="1.6" fill="rgba(247, 147, 26, 0.15)" />
    <circle cx="16" cy="14" r="1.2" fill="#f7931a" />
    <line x1="16" y1="8.5" x2="16" y2="10.5" stroke="#00f2fe" strokeWidth="1.2" strokeLinecap="round" />
    <line x1="16" y1="17.5" x2="16" y2="19.5" stroke="#00f2fe" strokeWidth="1.2" strokeLinecap="round" />
    <line x1="10.5" y1="14" x2="12.5" y2="14" stroke="#00f2fe" strokeWidth="1.2" strokeLinecap="round" />
    <line x1="19.5" y1="14" x2="21.5" y2="14" stroke="#00f2fe" strokeWidth="1.2" strokeLinecap="round" />
  </svg>
);

// 2. Original Cryptographic Token (Bitcoin-Forensic Ledger Coin — Not trademarked logo)
export const BTCCoinIcon = ({ size = 20, className = '', color = '#f7931a', ...props }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className={className}
    {...props}
  >
    <circle cx="12" cy="12" r="10" stroke={color} strokeWidth="1.75" strokeOpacity="0.85" />
    <circle cx="12" cy="12" r="7.5" stroke={color} strokeWidth="1" strokeDasharray="3 2" strokeOpacity="0.5" />
    {/* Cryptographic Key / Circuit Nodes */}
    <path
      d="M9 7.5H13.2C14.7 7.5 15.8 8.4 15.8 9.6C15.8 10.6 15.1 11.3 14.1 11.6C15.3 11.9 16.2 12.8 16.2 14.1C16.2 15.5 14.9 16.5 13.2 16.5H9"
      stroke={color}
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <line x1="11" y1="5.5" x2="11" y2="7.5" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
    <line x1="13.5" y1="5.5" x2="13.5" y2="7.5" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
    <line x1="11" y1="16.5" x2="11" y2="18.5" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
    <line x1="13.5" y1="16.5" x2="13.5" y2="18.5" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
  </svg>
);

// 3. Block Ledger Icon (Linked Cryptographic Block with Hash Merkle Root)
export const BlockLedgerIcon = ({ size = 20, className = '', color = 'currentColor', ...props }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className={className}
    {...props}
  >
    <path
      d="M12 2.5L20.5 7V17L12 21.5L3.5 17V7L12 2.5Z"
      stroke={color}
      strokeWidth="1.6"
      strokeLinejoin="round"
    />
    <path d="M12 2.5V21.5" stroke={color} strokeWidth="1.4" strokeOpacity="0.4" />
    <path d="M3.5 7L12 11.5L20.5 7" stroke={color} strokeWidth="1.4" strokeLinejoin="round" />
    {/* Internal Hash Links */}
    <circle cx="8" cy="14" r="1.2" fill={color} />
    <circle cx="16" cy="14" r="1.2" fill={color} />
    <circle cx="12" cy="7" r="1.2" fill={color} />
  </svg>
);

// 4. Typology: CoinJoin / Mixer Manifold (Inputs converge into shuffled entropy box)
export const CoinJoinIcon = ({ size = 20, className = '', color = '#f59e0b', ...props }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className={className}
    {...props}
  >
    {/* Converging Inputs */}
    <path d="M3 5H8L11 9H13" stroke={color} strokeWidth="1.6" strokeLinecap="round" />
    <path d="M3 12H8L11 11H13" stroke={color} strokeWidth="1.6" strokeLinecap="round" />
    <path d="M3 19H8L11 15H13" stroke={color} strokeWidth="1.6" strokeLinecap="round" />
    {/* Obfuscation Mixer Hub */}
    <rect x="10" y="8" width="4" height="8" rx="1.5" stroke={color} strokeWidth="1.4" fill="rgba(245, 158, 11, 0.2)" />
    {/* Shuffled Outputs */}
    <path d="M14 9H16L21 5" stroke={color} strokeWidth="1.6" strokeLinecap="round" />
    <path d="M14 12H17L21 12" stroke={color} strokeWidth="1.6" strokeLinecap="round" />
    <path d="M14 15H16L21 19" stroke={color} strokeWidth="1.6" strokeLinecap="round" />
  </svg>
);

// 5. Typology: Peel Chain (Continuous trunk peeling micro-payments)
export const PeelChainIcon = ({ size = 20, className = '', color = '#3b82f6', ...props }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className={className}
    {...props}
  >
    {/* Main Heavy Trunk Line */}
    <path d="M3 6H9L12 12H17L21 18" stroke={color} strokeWidth="2.2" strokeLinecap="round" />
    {/* Asymmetric Peeled Droplets */}
    <path d="M9 6V11L11 14" stroke="#f7931a" strokeWidth="1.4" strokeLinecap="round" strokeDasharray="2 2" />
    <circle cx="11" cy="15" r="1.5" fill="#f7931a" />
    <path d="M17 12V16L19 19" stroke="#f7931a" strokeWidth="1.4" strokeLinecap="round" strokeDasharray="2 2" />
    <circle cx="19" cy="20" r="1.5" fill="#f7931a" />
    {/* Origin & Terminus Nodes */}
    <circle cx="3" cy="6" r="2" fill={color} />
    <circle cx="21" cy="18" r="2" fill={color} />
  </svg>
);

// 6. Typology: Darknet Market (Tor Onion Layers + Encrypted Vault)
export const DarknetMarketIcon = ({ size = 20, className = '', color = '#ef4444', ...props }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className={className}
    {...props}
  >
    {/* Onion Encrypted Arcs */}
    <path d="M4 14C4 7.5 7.5 3 12 3C16.5 3 20 7.5 20 14" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
    <path d="M7 15C7 10 9 6.5 12 6.5C15 6.5 17 10 17 15" stroke={color} strokeWidth="1.3" strokeDasharray="2 2" />
    {/* Padlock Vault Base */}
    <rect x="8" y="13" width="8" height="7" rx="1.5" stroke={color} strokeWidth="1.6" fill="rgba(239, 68, 68, 0.15)" />
    <path d="M10 13V10.5C10 9.4 10.9 8.5 12 8.5C13.1 8.5 14 9.4 14 10.5V13" stroke={color} strokeWidth="1.4" />
    <circle cx="12" cy="16.5" r="1" fill={color} />
  </svg>
);

// 7. Typology: Ransomware Extortion (Locker Grid + Hazard Cross)
export const RansomwareIcon = ({ size = 20, className = '', color = '#ef4444', ...props }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className={className}
    {...props}
  >
    {/* Outer Warning Shield */}
    <path
      d="M12 2.5L21 6.5V13C21 18.5 17 21.8 12 23C7 21.8 3 18.5 3 13V6.5L12 2.5Z"
      stroke={color}
      strokeWidth="1.7"
      fill="rgba(239, 68, 68, 0.1)"
    />
    {/* Cryptographic Lock Clasp */}
    <rect x="9" y="12" width="6" height="6" rx="1" stroke={color} strokeWidth="1.5" fill={color} fillOpacity="0.25" />
    <path d="M10 12V9.5C10 8.4 10.9 7.5 12 7.5C13.1 7.5 14 8.4 14 9.5V12" stroke={color} strokeWidth="1.4" />
    {/* Keyhole dot */}
    <circle cx="12" cy="15" r="0.8" fill="#fff" />
  </svg>
);

// 8. Typology: Layering (Concentric Rapid-Hop Dispersal)
export const LayeringIcon = ({ size = 20, className = '', color = '#8b5cf6', ...props }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className={className}
    {...props}
  >
    {/* Concentric Strata Hopping */}
    <ellipse cx="12" cy="7" rx="8" ry="3.5" stroke={color} strokeWidth="1.5" />
    <ellipse cx="12" cy="12" rx="8" ry="3.5" stroke={color} strokeWidth="1.5" strokeDasharray="3 2" />
    <ellipse cx="12" cy="17" rx="8" ry="3.5" stroke={color} strokeWidth="1.5" />
    {/* Vertical Flow Hop Vector */}
    <path d="M12 5V19M12 19L9.5 16.5M12 19L14.5 16.5" stroke="#00f2fe" strokeWidth="1.6" strokeLinecap="round" />
  </svg>
);

// 9. Typology: Structuring / Smurfing (Sub-Threshold Bracketed Splits)
export const StructuringIcon = ({ size = 20, className = '', color = '#f59e0b', ...props }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className={className}
    {...props}
  >
    {/* Regulatory Threshold Ceiling Line */}
    <line x1="3" y1="7" x2="21" y2="7" stroke="#ef4444" strokeWidth="1.5" strokeDasharray="3 2" />
    {/* Main Inflow Splitting Under Threshold */}
    <circle cx="12" cy="3.5" r="1.5" fill="#00f2fe" />
    <path d="M12 4.5V9.5" stroke="#00f2fe" strokeWidth="1.5" strokeLinecap="round" />
    <path d="M12 9.5L6 14V19" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
    <path d="M12 9.5V19" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
    <path d="M12 9.5L18 14V19" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
    {/* Three sub-threshold droplets */}
    <circle cx="6" cy="19.5" r="1.5" fill={color} />
    <circle cx="12" cy="19.5" r="1.5" fill={color} />
    <circle cx="18" cy="19.5" r="1.5" fill={color} />
  </svg>
);

// 10. Typology: Dusting Attack (Microscopic Satoshi Particulate Spray)
export const DustingIcon = ({ size = 20, className = '', color = '#06b6d4', ...props }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className={className}
    {...props}
  >
    {/* Central Broadcaster Emitter */}
    <circle cx="5" cy="12" r="2.5" stroke={color} strokeWidth="1.6" fill="rgba(6, 182, 212, 0.2)" />
    {/* Radial Dust Stream Vectors */}
    <line x1="8" y1="11" x2="13" y2="7" stroke={color} strokeWidth="1.2" strokeDasharray="1.5 1.5" />
    <line x1="8.5" y1="12" x2="14" y2="12" stroke={color} strokeWidth="1.2" strokeDasharray="1.5 1.5" />
    <line x1="8" y1="13" x2="13" y2="17" stroke={color} strokeWidth="1.2" strokeDasharray="1.5 1.5" />
    {/* Scattered Target Dust Satoshis */}
    <circle cx="15.5" cy="6" r="1.2" fill="#f7931a" />
    <circle cx="18.5" cy="8.5" r="1" fill="#f7931a" />
    <circle cx="16.5" cy="12" r="1.2" fill="#f7931a" />
    <circle cx="19.5" cy="15" r="1" fill="#f7931a" />
    <circle cx="15.5" cy="18" r="1.2" fill="#f7931a" />
  </svg>
);

// 11. Typology: Wallet Cluster / CIOH Hull (Multi-Address Entity Cluster)
export const WalletClusterIcon = ({ size = 20, className = '', color = '#10b981', ...props }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className={className}
    {...props}
  >
    {/* Common-Input Clustering Hull Enclosure */}
    <path
      d="M7 4H17L21 11L18 19H6L2 11L7 4Z"
      stroke={color}
      strokeWidth="1.4"
      strokeDasharray="3 2"
      fill="rgba(16, 185, 129, 0.08)"
    />
    {/* Co-spending Member Addresses */}
    <circle cx="7" cy="8" r="1.8" fill={color} />
    <circle cx="17" cy="8" r="1.8" fill={color} />
    <circle cx="12" cy="13" r="2.2" stroke={color} strokeWidth="1.5" fill="rgba(16, 185, 129, 0.3)" />
    <circle cx="7" cy="16" r="1.8" fill={color} />
    <circle cx="17" cy="16" r="1.8" fill={color} />
    {/* Internal Intra-Cluster Links */}
    <line x1="7" y1="8" x2="12" y2="13" stroke={color} strokeWidth="1" strokeOpacity="0.6" />
    <line x1="17" y1="8" x2="12" y2="13" stroke={color} strokeWidth="1" strokeOpacity="0.6" />
    <line x1="7" y1="16" x2="12" y2="13" stroke={color} strokeWidth="1" strokeOpacity="0.6" />
    <line x1="17" y1="16" x2="12" y2="13" stroke={color} strokeWidth="1" strokeOpacity="0.6" />
  </svg>
);

// 12. Sealed Dossier / Evidence Docket (Wax Seal Rosette over Forensic Folder)
export const SealedDossierIcon = ({ size = 24, className = '', verified = false, ...props }) => {
  const sealColor = verified ? '#10b981' : '#ef4444';
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      {...props}
    >
      {/* Evidence Folder Backing */}
      <path
        d="M3 6.5C3 5.67 3.67 5 4.5 5H9.5L11.5 7.5H19.5C20.33 7.5 21 8.17 21 9V18.5C21 19.33 20.33 20 19.5 20H4.5C3.67 20 3 19.33 3 18.5V6.5Z"
        stroke="#94a3b8"
        strokeWidth="1.5"
        fill="rgba(15, 23, 42, 0.7)"
      />
      {/* Dossier Document Sheet Inside */}
      <line x1="6.5" y1="11" x2="13.5" y2="11" stroke="#64748b" strokeWidth="1.2" strokeLinecap="round" />
      <line x1="6.5" y1="14" x2="11" y2="14" stroke="#64748b" strokeWidth="1.2" strokeLinecap="round" />
      {/* Official Forensic Wax Seal Rosette */}
      <circle cx="16.5" cy="15.5" r="4.5" fill={sealColor} fillOpacity="0.25" stroke={sealColor} strokeWidth="1.5" />
      <path d="M15 15.5L16.2 16.7L18 14.5" stroke={sealColor} strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
};

// 13. Taint Flow Particle / Directed Satoshi Vector
export const TaintFlowIcon = ({ size = 20, className = '', color = '#ef4444', ...props }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className={className}
    {...props}
  >
    {/* Velocity Vector Stream */}
    <path d="M3 12H17M17 12L12 7M17 12L12 17" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    {/* Trailing Tainted Satoshi Drop */}
    <circle cx="20" cy="12" r="2.5" fill="#f7931a" stroke={color} strokeWidth="1" />
  </svg>
);

/**
 * Typology Icon Registry Helper
 * Maps detection rule codes and names to custom forensic SVG icons.
 */
export const getTypologyIcon = (typology, props = {}) => {
  const norm = String(typology || '').toLowerCase();
  if (norm.includes('coinjoin') || norm.includes('mixer') || norm.includes('t_coinjoin')) {
    return <CoinJoinIcon {...props} />;
  }
  if (norm.includes('peel') || norm.includes('t_peel_chain')) {
    return <PeelChainIcon {...props} />;
  }
  if (norm.includes('darknet') || norm.includes('t_darknet')) {
    return <DarknetMarketIcon {...props} />;
  }
  if (norm.includes('ransom') || norm.includes('t_ransomware')) {
    return <RansomwareIcon {...props} />;
  }
  if (norm.includes('layer') || norm.includes('t_layering')) {
    return <LayeringIcon {...props} />;
  }
  if (norm.includes('struct') || norm.includes('smurf') || norm.includes('t_structuring')) {
    return <StructuringIcon {...props} />;
  }
  if (norm.includes('dust') || norm.includes('t_dusting')) {
    return <DustingIcon {...props} />;
  }
  if (norm.includes('cluster') || norm.includes('cioh') || norm.includes('t_multi_cluster')) {
    return <WalletClusterIcon {...props} />;
  }
  // Default to BlockLedgerIcon for general blockchain alerts
  return <BlockLedgerIcon {...props} />;
};
