package models

// GenerateRequest represents the request for /api/generate endpoint
type GenerateRequest struct {
	Model   string                 `json:"model"`
	Prompt  string                 `json:"prompt"`
	System  *string                `json:"system,omitempty"`
	Stream  bool                   `json:"stream"`
	Options map[string]interface{} `json:"options,omitempty"`
}

// ChatMessage represents a single message in a chat conversation
type ChatMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// ChatRequest represents the request for /api/chat endpoint
type ChatRequest struct {
	Model    string                 `json:"model"`
	Messages []ChatMessage          `json:"messages"`
	Stream   bool                   `json:"stream"`
	Options  map[string]interface{} `json:"options,omitempty"`
}

// PullRequest represents the request for /api/pull endpoint
type PullRequest struct {
	Name string `json:"name"`
}

// ShowRequest represents the request for /api/show endpoint
type ShowRequest struct {
	Name string `json:"name"`
}

// BatchRequest represents a batch of requests for enhanced endpoint
type BatchRequest struct {
	Requests []BatchItem `json:"requests"`
}

// BatchItem represents a single item in a batch request
type BatchItem struct {
	ID      string      `json:"id"`
	Type    string      `json:"type"` // "generate" or "chat"
	Payload interface{} `json:"payload"`
}
