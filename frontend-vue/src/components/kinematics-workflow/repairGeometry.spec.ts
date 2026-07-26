import { describe, expect, it } from 'vitest'
import { pixelDistance, toIntrinsicPoint } from './repairGeometry'

describe('repair geometry', () => {
  it('maps CSS coordinates to intrinsic video pixels', () => {
    expect(toIntrinsicPoint(150, 75, { left: 50, top: 25, width: 200, height: 100 }, 1920, 1080))
      .toEqual({ x: 960, y: 540 })
  })

  it('clamps points to intrinsic bounds', () => {
    expect(toIntrinsicPoint(0, 0, { left: 50, top: 25, width: 200, height: 100 }, 1920, 1080))
      .toEqual({ x: 0, y: 0 })
  })

  it('calculates scale distance only for two points', () => {
    expect(pixelDistance([{ x: 0, y: 0 }, { x: 3, y: 4 }])).toBe(5)
    expect(pixelDistance([])).toBeNull()
  })
})
