package logging

import (
	"context"
	"log/slog"

	"github.com/google/uuid"
)

// ContextKey represents keys used in context for logging
type ContextKey string

const (
	// CorrelationIDKey is used to store correlation ID in context
	CorrelationIDKey ContextKey = "correlation_id"
	// RequestIDKey is used to store request ID in context
	RequestIDKey ContextKey = "request_id"
	// UserIDKey is used to store user ID in context
	UserIDKey ContextKey = "user_id"
)

// WithCorrelationID adds a correlation ID to the context
func WithCorrelationID(ctx context.Context, correlationID string) context.Context {
	if correlationID == "" {
		correlationID = uuid.New().String()
	}
	return context.WithValue(ctx, CorrelationIDKey, correlationID)
}

// GetCorrelationID retrieves correlation ID from context
func GetCorrelationID(ctx context.Context) string {
	if id, ok := ctx.Value(CorrelationIDKey).(string); ok {
		return id
	}
	return ""
}

// WithRequestID adds a request ID to the context
func WithRequestID(ctx context.Context, requestID string) context.Context {
	if requestID == "" {
		requestID = uuid.New().String()
	}
	return context.WithValue(ctx, RequestIDKey, requestID)
}

// GetRequestID retrieves request ID from context
func GetRequestID(ctx context.Context) string {
	if id, ok := ctx.Value(RequestIDKey).(string); ok {
		return id
	}
	return ""
}

// WithUserID adds a user ID to the context
func WithUserID(ctx context.Context, userID string) context.Context {
	return context.WithValue(ctx, UserIDKey, userID)
}

// GetUserID retrieves user ID from context
func GetUserID(ctx context.Context) string {
	if id, ok := ctx.Value(UserIDKey).(string); ok {
		return id
	}
	return ""
}

// LogWithContext creates a logger with context values
func LogWithContext(ctx context.Context, logger *slog.Logger) *slog.Logger {
	args := make([]any, 0, 6)

	if correlationID := GetCorrelationID(ctx); correlationID != "" {
		args = append(args, "correlation_id", correlationID)
	}

	if requestID := GetRequestID(ctx); requestID != "" {
		args = append(args, "request_id", requestID)
	}

	if userID := GetUserID(ctx); userID != "" {
		args = append(args, "user_id", userID)
	}

	return logger.With(args...)
}

// NewCorrelationID generates a new correlation ID
func NewCorrelationID() string {
	return uuid.New().String()
}

// NewRequestID generates a new request ID
func NewRequestID() string {
	return uuid.New().String()
}
