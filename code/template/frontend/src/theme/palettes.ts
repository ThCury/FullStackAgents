export type PaletteId = 'lime' | 'terracotta' | 'orange-blue'

export type AppPalette = { id: PaletteId; name: string; primary: string; secondary: string; accent: string; background: string; surface: string; textPrimary: string; border: string; textOnSurface: string }

export const palettes: AppPalette[] = [
  { id: 'lime', name: 'Lima', primary: '#D4ED57', secondary: '#FFFFFF', accent: '#5A6A18', background: '#ECEEF0', surface: '#DCE8AD', textPrimary: '#111827', border: '#BAC68A', textOnSurface: '#111827' },
  { id: 'terracotta', name: 'Terracota', primary: '#CC8066', secondary: '#FFFFFF', accent: '#334155', background: '#FFFFFF', surface: '#191C21', textPrimary: '#111827', border: '#CBD5E1', textOnSurface: '#FFFFFF' },
  { id: 'orange-blue', name: 'Laranja e azul', primary: '#F97316', secondary: '#000000', accent: '#3B82F6', background: '#F8F9FA', surface: '#191C21', textPrimary: '#111827', border: '#D1D5DB', textOnSurface: '#FFFFFF' },
]

export const defaultPaletteId: PaletteId = 'lime'
export function findPalette(id: PaletteId): AppPalette { return palettes.find((palette) => palette.id === id) ?? palettes[0] }
