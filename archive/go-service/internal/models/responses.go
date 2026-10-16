package models

import "time"

// TimingInfo represents performance timing information added to responses
type TimingInfo struct {
	ResponseTime float64 `json:"response_time"`
	Timestamp    float64 `json:"timestamp"`
}

// GenerateResponse represents the response from /api/generate endpoint
type GenerateResponse struct {
	Response           string     `json:"response"`
	Done               bool       `json:"done"`
	Context            []int      `json:"context,omitempty"`
	TotalDuration      int64      `json:"total_duration,omitempty"`
	LoadDuration       int64      `json:"load_duration,omitempty"`
	PromptEvalCount    int        `json:"prompt_eval_count,omitempty"`
	PromptEvalDuration int64      `json:"prompt_eval_duration,omitempty"`
	EvalCount          int        `json:"eval_count,omitempty"`
	EvalDuration       int64      `json:"eval_duration,omitempty"`
	Timing             TimingInfo `json:"_timing"`
}

// ChatResponseMessage represents the message in a chat response
type ChatResponseMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// ChatResponse represents the response from /api/chat endpoint
type ChatResponse struct {
	Message            ChatResponseMessage `json:"message"`
	Done               bool                `json:"done"`
	TotalDuration      int64               `json:"total_duration,omitempty"`
	LoadDuration       int64               `json:"load_duration,omitempty"`
	PromptEvalCount    int                 `json:"prompt_eval_count,omitempty"`
	PromptEvalDuration int64               `json:"prompt_eval_duration,omitempty"`
	EvalCount          int                 `json:"eval_count,omitempty"`
	EvalDuration       int64               `json:"eval_duration,omitempty"`
	Timing             TimingInfo          `json:"_timing"`
}

// ModelInfo represents detailed information about a model
type ModelInfo struct {
	Name       string                 `json:"name"`
	Size       int64                  `json:"size"`
	ModifiedAt time.Time              `json:"modified_at"`
	Digest     string                 `json:"digest,omitempty"`
	Details    map[string]interface{} `json:"details,omitempty"`
}

// TagsResponse represents the response from /api/tags endpoint
type TagsResponse struct {
	Models []ModelInfo `json:"models"`
}

// ShowResponse represents the response from /api/show endpoint
type ShowResponse struct {
	License    string                 `json:"license,omitempty"`
	Modelfile  string                 `json:"modelfile,omitempty"`
	Parameters string                 `json:"parameters,omitempty"`
	Template   string                 `json:"template,omitempty"`
	Details    map[string]interface{} `json:"details,omitempty"`
}

// PullResponse represents a status update during model pull
type PullResponse struct {
	Status    string `json:"status"`
	Digest    string `json:"digest,omitempty"`
	Total     int64  `json:"total,omitempty"`
	Completed int64  `json:"completed,omitempty"`
}

// BatchResponse represents the response from batch endpoint
type BatchResponse struct {
	Results []BatchResult `json:"results"`
}

// BatchResult represents a single result in a batch response
type BatchResult struct {
	ID     string      `json:"id"`
	Status string      `json:"status"` // "success" or "error"
	Result interface{} `json:"result,omitempty"`
	Error  string      `json:"error,omitempty"`
}

// ErrorResponse represents a standard error response
type ErrorResponse struct {
	Error   string `json:"error"`
	Details string `json:"details,omitempty"`
}
