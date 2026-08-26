import { ThemeProvider as MuiThemeProvider, createTheme } from '@mui/material'
import { ReactNode, createContext, useContext, useMemo, useState } from 'react'

import { AppPalette, PaletteId, defaultPaletteId, findPalette } from './palettes'

type ThemeSettings = { palette: AppPalette; selectPalette: (id: PaletteId) => void }
const ThemeSettingsContext = createContext<ThemeSettings | null>(null)
const storageKey = 'login-todo-palette'

export function ThemeSettingsProvider({ children }: { children: ReactNode }) {
  const [paletteId, setPaletteId] = useState<PaletteId>(() => {
    const stored = localStorage.getItem(storageKey) as PaletteId | null
    return stored ? findPalette(stored).id : defaultPaletteId
  })
  const palette = findPalette(paletteId)
  const theme = useMemo(() => createTheme({
    palette: { primary: { main: palette.primary, contrastText: palette.textPrimary }, secondary: { main: palette.accent, contrastText: palette.secondary }, background: { default: palette.background, paper: palette.secondary }, text: { primary: palette.textPrimary, secondary: palette.accent }, divider: palette.border },
    shape: { borderRadius: 12 },
    components: { MuiButton: { styleOverrides: { root: { textTransform: 'none', fontWeight: 700 } } } },
  }), [palette])
  const settings = { palette, selectPalette: (id: PaletteId) => { localStorage.setItem(storageKey, id); setPaletteId(id) } }
  return <ThemeSettingsContext.Provider value={settings}><MuiThemeProvider theme={theme}>{children}</MuiThemeProvider></ThemeSettingsContext.Provider>
}

export function useThemeSettings(): ThemeSettings {
  const settings = useContext(ThemeSettingsContext)
  if (settings === null) throw new Error('useThemeSettings deve ser usado dentro do ThemeSettingsProvider.')
  return settings
}
