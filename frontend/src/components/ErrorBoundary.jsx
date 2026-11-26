import { Component } from 'react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  render() {
    if (this.state.error) {
      return (
        <main className="app-error-boundary">
          <h1>Something went wrong</h1>
          <p>The dashboard could not be rendered. Reload the page to try again.</p>
          <button type="button" className="app-button" onClick={() => globalThis.location.reload()}>
            Reload
          </button>
        </main>
      )
    }
    return this.props.children
  }
}
