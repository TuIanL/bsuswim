export class PrintReadyRegistry {
  private pending = 0
  private resolved = 0
  private done = false

  addTask(label?: string): () => void {
    this.pending += 1
    let called = false

    return () => {
      if (called || this.done) return
      called = true
      this.resolved += 1
      this.check()
    }
  }

  private check() {
    if (this.done) return
    if (this.resolved >= this.pending) {
      this.markReady()
    }
  }

  private markReady() {
    if (this.done) return
    this.done = true
    ;(window as any).__REPORT_PRINT_READY__ = true
  }

  startTimeout(ms = 30000) {
    window.setTimeout(() => {
      if (!this.done) {
        console.warn('[PrintReadyRegistry] Timeout reached, forcing ready')
        this.markReady()
      }
    }, ms)
  }

  get isDone() {
    return this.done
  }
}
