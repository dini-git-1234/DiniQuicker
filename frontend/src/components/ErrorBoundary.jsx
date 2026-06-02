import React from "react";

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    // Keep console logging for developers; UI shows friendly message.
    // eslint-disable-next-line no-console
    console.error("UI crashed:", error, errorInfo);
  }

  reset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 24, maxWidth: 720, margin: "0 auto" }}>
          <h2 style={{ marginTop: 0 }}>משהו השתבש במסך</h2>
          <p>אפשר לנסות לרענן את הדף או ללחוץ על “נסה שוב”.</p>
          <button onClick={this.reset} style={{ padding: "8px 12px" }}>
            נסה שוב
          </button>
          {this.state.error?.message ? (
            <pre
              style={{
                marginTop: 16,
                padding: 12,
                background: "#f6f8fa",
                overflow: "auto",
              }}
            >
              {this.state.error.message}
            </pre>
          ) : null}
        </div>
      );
    }

    return this.props.children;
  }
}

