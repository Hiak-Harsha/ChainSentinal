import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FolderOpen, Clock, MapPin } from 'lucide-react';

/**
 * Entity type → color map matching CSS variables.
 */
const ENTITY_COLORS = {
  EXCHANGE: 'var(--entity-exchange)',
  MIXER: 'var(--entity-mixer)',
  MINING_POOL: 'var(--entity-mining)',
  SERVICE: 'var(--entity-service)',
  WALLET: 'var(--entity-wallet)',
  UNKNOWN: 'var(--entity-unknown)',
};

function truncateId(id, maxLen = 16) {
  if (!id || id.length <= maxLen) return id;
  return `${id.slice(0, 8)}\u2026${id.slice(-6)}`;
}

export default function ContextRail({
  recentEntities = [],
  activeCase = null,
  selection,
  onPivotTo,
}) {
  return (
    <aside className="context-rail" id="context-rail">
      {/* Active Case Docket */}
      {activeCase && (
        <div className="rail-section">
          <div className="rail-section-title">
            <FolderOpen size={11} style={{ marginRight: 4, verticalAlign: -1 }} />
            Active Case
          </div>
          <div
            className="rail-entity-item"
            style={{ borderLeft: '2px solid var(--btc-orange)' }}
            onClick={() => onPivotTo({ mode: 'network', selection: { type: 'case', id: activeCase.case_id } })}
          >
            <div style={{ fontSize: '0.76rem', fontWeight: 700, color: 'var(--text-main)' }}>
              {activeCase.title || `Case ${truncateId(activeCase.case_id)}`}
            </div>
          </div>
          {activeCase.entity_count !== undefined && (
            <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)', padding: '0 0.5rem', marginTop: 2 }}>
              {activeCase.entity_count} entities tracked
            </div>
          )}
        </div>
      )}

      <div className="rail-divider" />

      {/* Recent Entity Quick-Pivots */}
      <div className="rail-section">
        <div className="rail-section-title">
          <Clock size={10} style={{ marginRight: 4, verticalAlign: -1 }} />
          Recent Entities
        </div>

        {recentEntities.length === 0 && (
          <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', padding: '0.5rem', textAlign: 'center' }}>
            No recent entities
          </div>
        )}

        <AnimatePresence>
          {recentEntities.slice(0, 8).map((ent) => {
            const isSelected = selection?.type === 'entity' && selection?.id === ent.entity_id;
            const dotColor = ENTITY_COLORS[ent.entity_type] || ENTITY_COLORS.UNKNOWN;
            return (
              <motion.div
                key={ent.entity_id}
                className={`rail-entity-item ${isSelected ? 'selected' : ''}`}
                onClick={() =>
                  onPivotTo({ mode: 'network', selection: { type: 'entity', id: ent.entity_id } })
                }
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                transition={{ duration: 0.15 }}
              >
                <span className="rail-entity-dot" style={{ backgroundColor: dotColor }} />
                <span className="rail-entity-id">{truncateId(ent.entity_id)}</span>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>

      <div className="rail-divider" />

      {/* Saved Query Filters (placeholder, reads localStorage in future) */}
      <div className="rail-section">
        <div className="rail-section-title">
          <MapPin size={10} style={{ marginRight: 4, verticalAlign: -1 }} />
          Saved Filters
        </div>
        <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', padding: '0.5rem', textAlign: 'center' }}>
          No saved filters yet
        </div>
      </div>
    </aside>
  );
}
