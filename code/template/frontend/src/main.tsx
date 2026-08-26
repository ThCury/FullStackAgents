import '@fontsource/roboto/400.css'
import '@fontsource/roboto/500.css'
import '@fontsource/roboto/700.css'
import { CssBaseline } from '@mui/material'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import App from './App'
import { ThemeSettingsProvider } from './theme/ThemeSettingsProvider'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeSettingsProvider>
      <CssBaseline />
      <App />
    </ThemeSettingsProvider>
  </StrictMode>,
)
