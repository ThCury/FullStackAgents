import PaletteIcon from '@mui/icons-material/Palette'
import { FormControl, InputLabel, MenuItem, Select, Stack } from '@mui/material'

import { PaletteId, palettes } from '../../theme/palettes'
import { useThemeSettings } from '../../theme/ThemeSettingsProvider'

export function PaletteSelector() {
  const { palette, selectPalette } = useThemeSettings()
  return <Stack direction="row" alignItems="center" spacing={1}><PaletteIcon fontSize="small" /><FormControl size="small" sx={{ minWidth: 150 }}><InputLabel id="palette-label">Paleta</InputLabel><Select labelId="palette-label" label="Paleta" value={palette.id} onChange={(event) => selectPalette(event.target.value as PaletteId)}>{palettes.map((option) => <MenuItem key={option.id} value={option.id}>{option.name}</MenuItem>)}</Select></FormControl></Stack>
}
