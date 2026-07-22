export class PrintReadyRegistry {
  private pending = 0
  private resolved = 0
  private done = false
  private completeHandler: (() => void) | null = null
  private timeoutHandler: (() => void) | null = null

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
    if (this.completeHandler) this.completeHandler()
  }

  onComplete(handler: () => void) {
    this.completeHandler = handler
    if (this.done) handler()
  }

  onTimeout(handler: () => void) {
    this.timeoutHandler = handler
  }

  startTimeout(ms = 30000) {
    window.setTimeout(() => {
      if (!this.done) {
        // Do NOT force ready on timeout. Signal failure so export is blocked.
        if (this.timeoutHandler) this.timeoutHandler()
      }
    }, ms)
  }

  get isDone() {
    return this.done
  }
}
