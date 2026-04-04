import { describe, it, expect } from 'vitest'
import { getStepConfig, formatModelShort } from '@/lib/task-utils'

describe('getStepConfig', () => {
  it('returns correct config for known step "enrichment"', () => {
    const config = getStepConfig('enrichment')
    expect(config.label).toBe('Enriqueciendo')
    expect(config.description).toBe('Buscando información pública del negocio')
  })

  it('returns correct config for known step "scoring"', () => {
    const config = getStepConfig('scoring')
    expect(config.label).toBe('Puntuando')
  })

  it('returns fallback with humanized label for unknown step', () => {
    const config = getStepConfig('unknown_step')
    expect(config.label).toBe('unknown step')
    expect(config.description).toBe('')
  })

  it('returns "Procesando" fallback for null input', () => {
    const config = getStepConfig(null)
    expect(config.label).toBe('Procesando')
    expect(config.description).toBe('Tarea en curso')
  })

  it('returns "Procesando" fallback for undefined input', () => {
    const config = getStepConfig(undefined)
    expect(config.label).toBe('Procesando')
  })
})

describe('formatModelShort', () => {
  it('extracts size suffix from model with colon notation', () => {
    // The regex matches `:` followed by digits and b/B
    expect(formatModelShort('provider:7b')).toBe('7B')
  })

  it('extracts uppercase B suffix', () => {
    expect(formatModelShort('ollama:llama3:70B')).toBe('70B')
  })

  it('returns the part after the last colon uppercased when no size match', () => {
    expect(formatModelShort('anthropic:claude-3-5-sonnet')).toBe('CLAUDE-3-5-SONNET')
  })

  it('returns the model itself when no colon present', () => {
    expect(formatModelShort('gpt4')).toBe('GPT4')
  })
})
