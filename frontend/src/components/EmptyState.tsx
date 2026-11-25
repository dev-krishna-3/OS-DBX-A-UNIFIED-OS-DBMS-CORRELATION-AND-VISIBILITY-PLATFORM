import { Search, ShieldAlert, Sparkles, Database, Play } from 'lucide-react';

export interface EmptyStateProps {
  icon?: 'search' | 'shield' | 'database' | 'sparkles';
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  secondaryActionLabel?: string;
  onSecondaryAction?: () => void;
}

export default function EmptyState({
  icon = 'search',
  title,
  description,
  actionLabel,
  onAction,
  secondaryActionLabel,
  onSecondaryAction,
}: EmptyStateProps) {
  const renderIcon = () => {
    switch (icon) {
      case 'shield':
        return <ShieldAlert size={36} strokeWidth={1.75} />;
      case 'database':
        return <Database size={36} strokeWidth={1.75} />;
      case 'sparkles':
        return <Sparkles size={36} strokeWidth={1.75} />;
      case 'search':
      default:
        return <Search size={36} strokeWidth={1.75} />;
    }
  };

  return (
    <div className="osdbx-empty-state" role="status" aria-label={title}>
      <div className="empty-state-graphic">
        <div className="empty-state-glow" aria-hidden="true" />
        <div className="empty-state-icon-box">{renderIcon()}</div>
      </div>
      <h3 className="empty-state-title">{title}</h3>
      <p className="empty-state-description">{description}</p>
      {(actionLabel || secondaryActionLabel) && (
        <div className="empty-state-actions">
          {actionLabel && (
            <button
              type="button"
              className="button button-primary"
              onClick={onAction}
            >
              <Play size={14} fill="currentColor" /> {actionLabel}
            </button>
          )}
          {secondaryActionLabel && (
            <button
              type="button"
              className="button button-secondary"
              onClick={onSecondaryAction}
            >
              {secondaryActionLabel}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
