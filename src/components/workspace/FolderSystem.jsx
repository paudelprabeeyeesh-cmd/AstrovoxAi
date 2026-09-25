import { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Icon from '../../design/Iconography'

export default function FolderSystem({ folders, activeFolder, onSelectFolder, onCreateFolder, onRenameFolder, onDeleteFolder }) {
  const [isCreating, setIsCreating] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')
  const [editingId, setEditingId] = useState(null)
  const [editName, setEditName] = useState('')

  const handleCreate = useCallback(() => {
    if (newFolderName.trim()) {
      onCreateFolder?.({ name: newFolderName.trim(), createdAt: new Date().toISOString() })
      setNewFolderName('')
      setIsCreating(false)
    }
  }, [newFolderName, onCreateFolder])

  const handleRename = useCallback((id) => {
    if (editName.trim()) {
      onRenameFolder?.(id, editName.trim())
    }
    setEditingId(null)
    setEditName('')
  }, [editName, onRenameFolder])

  return (
    <div
      style={{
        padding: '12px',
        backgroundColor: 'var(--astrovox-surface)',
        border: '1px solid var(--astrovox-border)',
        borderRadius: 'var(--astrovox-radius-lg)'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Icon name="folder" size={18} style={{ color: 'var(--astrovox-primary)' }} />
          <span style={{ fontSize: '13px', fontWeight: '600', color: 'var(--astrovox-text)' }}>
            Folders
          </span>
        </div>
        <button
          onClick={() => setIsCreating(true)}
          style={{
            padding: '4px 10px',
            backgroundColor: 'var(--astrovox-primary)',
            color: 'var(--astrovox-bg)',
            border: 'none',
            borderRadius: 'var(--astrovox-radius-sm)',
            cursor: 'pointer',
            fontSize: '11px',
            fontFamily: 'inherit',
            fontWeight: '600',
            display: 'flex',
            alignItems: 'center',
            gap: '4px'
          }}
        >
          <Icon name="plus" size={12} /> New
        </button>
      </div>

      <AnimatePresence>
        {isCreating && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            style={{ marginBottom: '8px' }}
          >
            <input
              autoFocus
              value={newFolderName}
              onChange={(e) => setNewFolderName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleCreate()
                if (e.key === 'Escape') { setIsCreating(false); setNewFolderName('') }
              }}
              placeholder="Folder name..."
              style={{
                width: '100%',
                padding: '8px 12px',
                backgroundColor: 'var(--astrovox-bg)',
                border: '1px solid var(--astrovox-primary)',
                borderRadius: 'var(--astrovox-radius-md)',
                color: 'var(--astrovox-text)',
                fontSize: '12px',
                fontFamily: 'inherit',
                outline: 'none'
              }}
            />
          </motion.div>
        )}
      </AnimatePresence>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        {folders.map((folder, index) => (
          <motion.div
            key={folder.id}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.03 }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 12px',
              backgroundColor: activeFolder === folder.id ? 'var(--astrovox-surface-hover)' : 'transparent',
              border: `1px solid ${activeFolder === folder.id ? 'var(--astrovox-primary)' : 'transparent'}`,
              borderRadius: 'var(--astrovox-radius-md)',
              cursor: 'pointer',
              transition: 'all 0.2s'
            }}
            onClick={() => onSelectFolder(folder.id)}
            onDoubleClick={() => { setEditingId(folder.id); setEditName(folder.name) }}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => { if (e.key === 'Enter') onSelectFolder(folder.id) }}
          >
            <Icon name="folder" size={16} style={{ color: 'var(--astrovox-primary)', flexShrink: 0 }} />
            {editingId === folder.id ? (
              <input
                autoFocus
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                onBlur={() => handleRename(folder.id)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleRename(folder.id)
                  if (e.key === 'Escape') setEditingId(null)
                }}
                style={{
                  flex: 1,
                  background: 'transparent',
                  border: 'none',
                  borderBottom: '1px solid var(--astrovox-primary)',
                  color: 'var(--astrovox-text)',
                  fontSize: '12px',
                  fontFamily: 'inherit',
                  outline: 'none'
                }}
                onClick={(e) => e.stopPropagation()}
              />
            ) : (
              <>
                <span style={{ flex: 1, fontSize: '12px', color: 'var(--astrovox-text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {folder.name}
                </span>
                <button
                  onClick={(e) => { e.stopPropagation(); onDeleteFolder?.(folder.id) }}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--astrovox-text-muted)',
                    cursor: 'pointer',
                    padding: '2px',
                    borderRadius: 'var(--astrovox-radius-sm)',
                    display: 'flex',
                    alignItems: 'center',
                    opacity: 0.6
                  }}
                  aria-label={`Delete ${folder.name}`}
                >
                  <Icon name="trash" size={12} />
                </button>
              </>
            )}
          </motion.div>
        ))}
      </div>
    </div>
  )
}
