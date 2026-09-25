export function getInitials(name) {
  if (!name || typeof name !== 'string') return '?'
  const parts = name.trim().split(/\s+/)
  if (parts.length >= 2) {
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
  }
  return name.slice(0, 2).toUpperCase()
}

export function stringToColor(str) {
  if (!str) return '#64748b'
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash)
  }
  const hue = Math.abs(hash % 360)
  const saturation = 60 + (Math.abs(hash) % 20)
  const lightness = 45 + (Math.abs(hash >> 2) % 15)
  return `hsl(${hue}, ${saturation}%, ${lightness}%)`
}

export function getContrastColor(hslColor) {
  const match = hslColor.match(/hsl\((\d+),\s*(\d+)%,\s*(\d+)%\)/)
  if (!match) return '#ffffff'
  const lightness = parseInt(match[3])
  return lightness > 60 ? '#0f172a' : '#ffffff'
}
