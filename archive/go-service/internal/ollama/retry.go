package ollama

import (
	"context"
	"fmt"
	"net"
	"net/http"
	"net/url"
	"sync"
	"syscall"
	"time"
)

// RetryConfig holds configuration for retry logic
type RetryConfig struct {
	MaxAttempts int
	BaseDelay   time.Duration
	MaxDelay    time.Duration
}

// DefaultRetryConfig returns a sensible default retry configuration
func DefaultRetryConfig() RetryConfig {
	return RetryConfig{
		MaxAttempts: 3,
		BaseDelay:   100 * time.Millisecond,
		MaxDelay:    5 * time.Second,
	}
}

// RetryableError represents an error that can be retried
type RetryableError struct {
	Err     error
	Attempt int
}

func (r RetryableError) Error() string {
	return fmt.Sprintf("attempt %d: %v", r.Attempt, r.Err)
}

// IsRetryable determines if an error is worth retrying
func IsRetryable(err error) bool {
	if err == nil {
		return false
	}

	// Network errors that are typically transient
	if netErr, ok := err.(net.Error); ok {
		return netErr.Timeout() || netErr.Temporary()
	}

	// Connection errors
	if opErr, ok := err.(*net.OpError); ok {
		return opErr.Temporary()
	}

	// DNS errors
	if dnsErr, ok := err.(*net.DNSError); ok {
		return dnsErr.Temporary()
	}

	// URL errors (wrapping other errors)
	if urlErr, ok := err.(*url.Error); ok {
		return IsRetryable(urlErr.Err)
	}

	// System call errors
	if err == syscall.ECONNREFUSED ||
		err == syscall.ECONNRESET ||
		err == syscall.EPIPE {
		return true
	}

	// HTTP client specific errors
	if err == http.ErrHandlerTimeout {
		return true
	}

	return false
}

// CalculateBackoff calculates the backoff duration for a given attempt
func CalculateBackoff(attempt int, config RetryConfig) time.Duration {
	if attempt <= 0 {
		return 0
	}

	// Exponential backoff with jitter
	delay := config.BaseDelay
	for i := 1; i < attempt && delay < config.MaxDelay; i++ {
		delay *= 2
	}

	if delay > config.MaxDelay {
		delay = config.MaxDelay
	}

	// Add jitter (up to 10% of the delay)
	jitter := time.Duration(float64(delay) * 0.1)
	if jitter > 0 {
		delay += time.Duration(time.Now().UnixNano() % int64(jitter))
	}

	return delay
}

// RetryFunc is a function that can be retried
type RetryFunc func() error

// WithRetry executes a function with retry logic
func WithRetry(ctx context.Context, config RetryConfig, fn RetryFunc) error {
	var lastErr error

	for attempt := 1; attempt <= config.MaxAttempts; attempt++ {
		// Check if context is cancelled before each attempt
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}

		err := fn()
		if err == nil {
			return nil
		}

		lastErr = &RetryableError{
			Err:     err,
			Attempt: attempt,
		}

		// Don't retry if it's not a retryable error
		if !IsRetryable(err) {
			break
		}

		// Don't sleep after the last attempt
		if attempt < config.MaxAttempts {
			backoff := CalculateBackoff(attempt, config)
			select {
			case <-ctx.Done():
				return ctx.Err()
			case <-time.After(backoff):
				// Continue to next attempt
			}
		}
	}

	return lastErr
}

// CircuitBreaker provides circuit breaker functionality
type CircuitBreaker struct {
	maxFailures  int
	resetTimeout time.Duration
	failures     int
	lastFailTime time.Time
	state        string // "closed", "open", "half-open"
	mu           sync.RWMutex
}

// NewCircuitBreaker creates a new circuit breaker
func NewCircuitBreaker(maxFailures int, resetTimeout time.Duration) *CircuitBreaker {
	return &CircuitBreaker{
		maxFailures:  maxFailures,
		resetTimeout: resetTimeout,
		state:        "closed",
	}
}

// Call executes a function through the circuit breaker
func (cb *CircuitBreaker) Call(fn func() error) error {
	cb.mu.RLock()
	state := cb.state
	lastFailTime := cb.lastFailTime
	cb.mu.RUnlock()

	// Check if we should transition from open to half-open
	if state == "open" && time.Since(lastFailTime) > cb.resetTimeout {
		cb.mu.Lock()
		if cb.state == "open" {
			cb.state = "half-open"
		}
		cb.mu.Unlock()
	}

	// Reject calls if circuit is open
	if state == "open" {
		return fmt.Errorf("circuit breaker is open")
	}

	// Execute the function
	err := fn()

	cb.mu.Lock()
	defer cb.mu.Unlock()

	if err != nil {
		cb.failures++
		cb.lastFailTime = time.Now()

		if cb.failures >= cb.maxFailures {
			cb.state = "open"
		}
		return err
	}

	// Reset on success
	if cb.state == "half-open" {
		cb.state = "closed"
	}
	cb.failures = 0

	return nil
}
