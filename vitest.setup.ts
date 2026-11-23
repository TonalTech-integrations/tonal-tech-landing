import '@testing-library/jest-dom/vitest'

// React 19: habilita act() en el entorno de pruebas
Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true })
