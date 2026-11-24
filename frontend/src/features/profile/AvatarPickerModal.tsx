import { useState, useRef, type ChangeEvent } from 'react';
import { Camera, Check, RotateCcw, Upload, X, Sparkles } from 'lucide-react';
import { CARTOON_AVATARS, resizeImageFile } from '../../utils/cartoonAvatars';
import { authApi } from '../../api';
import type { AuthUser } from '../../api/auth';

interface AvatarPickerModalProps {
  user: AuthUser;
  isOpen: boolean;
  onClose: () => void;
  onAvatarUpdated: (updatedUser: AuthUser) => void;
}

export default function AvatarPickerModal({
  user,
  isOpen,
  onClose,
  onAvatarUpdated,
}: AvatarPickerModalProps) {
  const [selectedAvatar, setSelectedAvatar] = useState<string | null>(user.avatar_url || null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [uploadName, setUploadName] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFileChange = async (event: ChangeEvent<HTMLInputElement>): Promise<void> => {
    const files = event.target.files;
    if (!files || files.length === 0) return;
    const file = files[0];

    if (!file.type.startsWith('image/')) {
      setError('Please select an image file (PNG, JPG, WebP, SVG).');
      return;
    }

    try {
      setBusy(true);
      setError('');
      const dataUrl = await resizeImageFile(file, 256);
      setSelectedAvatar(dataUrl);
      setUploadName(file.name);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not process that image file.');
    } finally {
      setBusy(false);
    }
  };

  const handleSave = async (): Promise<void> => {
    setBusy(true);
    setError('');
    try {
      const updated = await authApi.updateAvatar(selectedAvatar);
      // Also cache in localStorage for instant access across tabs
      if (selectedAvatar) {
        localStorage.setItem(`osdbx_avatar_${user.username}`, selectedAvatar);
      } else {
        localStorage.removeItem(`osdbx_avatar_${user.username}`);
      }
      onAvatarUpdated(updated);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save profile picture. Try again.');
    } finally {
      setBusy(false);
    }
  };

  const handleResetToInitials = (): void => {
    setSelectedAvatar(null);
    setUploadName('');
    setError('');
  };

  return (
    <div
      className="inspector-overlay"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Change profile picture"
      style={{ zIndex: 1100 }}
    >
      <div
        className="inspector-card"
        onClick={(e) => e.stopPropagation()}
        style={{
          maxWidth: '520px',
          width: '100%',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          padding: '0',
          overflow: 'hidden',
          borderRadius: '16px',
        }}
      >
        {/* Modal Header */}
        <div
          style={{
            padding: '18px 24px',
            borderBottom: '1px solid var(--color-rule, #e2e8f0)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'var(--color-paper, #ffffff)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span
              style={{
                display: 'grid',
                placeItems: 'center',
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                background: 'rgba(99, 102, 241, 0.1)',
                color: 'var(--color-primary, #6366f1)',
              }}
            >
              <Camera size={18} />
            </span>
            <div>
              <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 700, color: 'var(--color-ink)' }}>
                Profile Picture
              </h3>
              <p style={{ margin: 0, fontSize: '12px', color: 'var(--color-muted)' }}>
                Choose a cartoon character or upload your own photo
              </p>
            </div>
          </div>
          <button
            type="button"
            className="icon-button"
            onClick={onClose}
            aria-label="Close"
            style={{ border: 'none', background: 'transparent', cursor: 'pointer', color: 'var(--color-muted)' }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div
          style={{
            padding: '20px 24px',
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: '20px',
          }}
        >
          {/* Active Preview */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '16px',
              padding: '16px',
              borderRadius: '12px',
              background: 'var(--color-paper-2, #f8fafc)',
              border: '1px solid var(--color-rule, #e2e8f0)',
            }}
          >
            <div
              style={{
                width: '72px',
                height: '72px',
                borderRadius: '50%',
                overflow: 'hidden',
                flexShrink: 0,
                boxShadow: '0 4px 14px rgba(0,0,0,0.1)',
                border: '3px solid #ffffff',
                display: 'grid',
                placeItems: 'center',
                background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                color: '#ffffff',
                fontWeight: 800,
                fontSize: '24px',
              }}
            >
              {selectedAvatar ? (
                <img
                  src={selectedAvatar}
                  alt={user.username}
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                />
              ) : (
                user.username.slice(0, 2).toUpperCase()
              )}
            </div>

            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <strong style={{ fontSize: '15px', color: 'var(--color-ink)' }}>{user.username}</strong>
                <span
                  style={{
                    fontSize: '11px',
                    padding: '2px 8px',
                    borderRadius: '12px',
                    background: selectedAvatar ? 'rgba(99, 102, 241, 0.1)' : 'rgba(100, 116, 139, 0.1)',
                    color: selectedAvatar ? 'var(--color-primary, #6366f1)' : 'var(--color-muted)',
                    fontWeight: 600,
                  }}
                >
                  {selectedAvatar ? (uploadName ? 'Custom Upload' : 'Cartoon Character') : 'Initials Default'}
                </span>
              </div>
              <p style={{ margin: '4px 0 0', fontSize: '12px', color: 'var(--color-muted)' }}>
                {uploadName ? `File: ${uploadName}` : 'Preview of how your avatar appears across OS-DBX'}
              </p>
            </div>

            {selectedAvatar && (
              <button
                type="button"
                onClick={handleResetToInitials}
                title="Reset to default initials"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '5px',
                  padding: '6px 10px',
                  borderRadius: '8px',
                  border: '1px solid var(--color-rule, #cbd5e1)',
                  background: '#ffffff',
                  color: 'var(--color-muted)',
                  fontSize: '11px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                <RotateCcw size={12} /> Reset
              </button>
            )}
          </div>

          {/* Upload Custom Picture Option */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-ink)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Upload size={14} /> Upload Custom Photo
              </span>
              <span style={{ fontSize: '11px', color: 'var(--color-muted)' }}>PNG, JPG, WebP, SVG</span>
            </div>

            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept="image/png,image/jpeg,image/webp,image/svg+xml,image/gif"
              style={{ display: 'none' }}
            />

            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={busy}
              style={{
                width: '100%',
                padding: '12px 16px',
                borderRadius: '10px',
                border: '1.5px dashed var(--color-primary, #6366f1)',
                background: 'rgba(99, 102, 241, 0.04)',
                color: 'var(--color-primary, #6366f1)',
                fontSize: '13px',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                cursor: 'pointer',
                transition: 'background 150ms ease',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(99, 102, 241, 0.09)')}
              onMouseLeave={(e) => (e.currentTarget.style.background = 'rgba(99, 102, 241, 0.04)')}
            >
              <Upload size={16} /> Choose picture from device…
            </button>
          </div>

          {/* Cartoon Character Presets */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '10px' }}>
              <Sparkles size={14} style={{ color: '#f59e0b' }} />
              <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-ink)' }}>
                Cartoon Characters
              </span>
              <span style={{ fontSize: '11px', color: 'var(--color-muted)', marginLeft: 'auto' }}>
                Click to select
              </span>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(4, 1fr)',
                gap: '12px',
              }}
            >
              {CARTOON_AVATARS.map((avatar) => {
                const isSelected = selectedAvatar === avatar.svgDataUrl;
                return (
                  <button
                    key={avatar.id}
                    type="button"
                    onClick={() => {
                      setSelectedAvatar(avatar.svgDataUrl);
                      setUploadName('');
                      setError('');
                    }}
                    style={{
                      position: 'relative',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '10px 6px',
                      borderRadius: '12px',
                      border: isSelected ? '2px solid var(--color-primary, #6366f1)' : '1px solid var(--color-rule, #e2e8f0)',
                      background: isSelected ? 'rgba(99, 102, 241, 0.08)' : 'var(--color-paper, #ffffff)',
                      cursor: 'pointer',
                      transition: 'all 160ms ease',
                      outline: 'none',
                    }}
                  >
                    <div
                      style={{
                        position: 'relative',
                        width: '56px',
                        height: '56px',
                        borderRadius: '50%',
                        overflow: 'hidden',
                        boxShadow: isSelected ? '0 0 0 3px rgba(99, 102, 241, 0.25)' : 'none',
                      }}
                    >
                      <img
                        src={avatar.svgDataUrl}
                        alt={avatar.name}
                        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                      />
                      {isSelected && (
                        <div
                          style={{
                            position: 'absolute',
                            bottom: '0',
                            right: '0',
                            width: '18px',
                            height: '18px',
                            borderRadius: '50%',
                            background: 'var(--color-primary, #6366f1)',
                            color: '#ffffff',
                            display: 'grid',
                            placeItems: 'center',
                            border: '1.5px solid #ffffff',
                          }}
                        >
                          <Check size={11} strokeWidth={3} />
                        </div>
                      )}
                    </div>
                    <span
                      style={{
                        fontSize: '11px',
                        fontWeight: isSelected ? 700 : 500,
                        color: isSelected ? 'var(--color-primary, #6366f1)' : 'var(--color-ink)',
                        textAlign: 'center',
                        lineHeight: 1.2,
                      }}
                    >
                      {avatar.name}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {error && (
            <div
              style={{
                padding: '8px 12px',
                borderRadius: '8px',
                background: '#fef2f2',
                border: '1px solid #fecaca',
                color: '#991b1b',
                fontSize: '12px',
              }}
            >
              {error}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div
          style={{
            padding: '14px 24px',
            borderTop: '1px solid var(--color-rule, #e2e8f0)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-end',
            gap: '10px',
            background: 'var(--color-paper, #ffffff)',
          }}
        >
          <button
            type="button"
            onClick={onClose}
            disabled={busy}
            style={{
              padding: '8px 16px',
              borderRadius: '8px',
              border: '1px solid var(--color-rule, #cbd5e1)',
              background: '#ffffff',
              color: 'var(--color-ink)',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={busy}
            style={{
              padding: '8px 20px',
              borderRadius: '8px',
              border: 'none',
              background: 'var(--color-primary, #6366f1)',
              color: '#ffffff',
              fontSize: '13px',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              opacity: busy ? 0.7 : 1,
            }}
          >
            <Check size={15} />
            {busy ? 'Saving…' : 'Save Picture'}
          </button>
        </div>
      </div>
    </div>
  );
}
