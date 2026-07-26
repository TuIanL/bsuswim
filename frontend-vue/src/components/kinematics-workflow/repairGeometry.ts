export interface RepairPoint {
  x: number
  y: number
}

export function toIntrinsicPoint(
  clientX: number,
  clientY: number,
  rect: Pick<DOMRect, 'left' | 'top' | 'width' | 'height'>,
  width: number,
  height: number
): RepairPoint {
  return {
    x: Math.max(0, Math.min(width - 1, (clientX - rect.left) * width / rect.width)),
    y: Math.max(0, Math.min(height - 1, (clientY - rect.top) * height / rect.height))
  }
}

export function pixelDistance(points: RepairPoint[]): number | null {
  if (points.length !== 2) return null
  return Math.hypot(points[1].x - points[0].x, points[1].y - points[0].y)
}
