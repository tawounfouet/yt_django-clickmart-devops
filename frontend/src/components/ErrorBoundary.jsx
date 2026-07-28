import { Component } from "react";

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="container mt-5 text-center">
          <h2>Une erreur est survenue</h2>
          <p className="text-muted">{this.state.error?.message}</p>
          <button
            className="btn btn-primary"
            onClick={() => window.location.reload()}
          >
            Recharger la page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
