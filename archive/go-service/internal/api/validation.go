package api

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strings"

	"go-service/internal/models"
)

// writeJSONResponse writes a JSON response
func writeJSONResponse(w http.ResponseWriter, data interface{}, statusCode int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)

	if err := json.NewEncoder(w).Encode(data); err != nil {
		http.Error(w, "Failed to encode response", http.StatusInternalServerError)
	}
}

// writeErrorResponse writes a standardized error response
func writeErrorResponse(w http.ResponseWriter, message string, statusCode int) {
	errorResp := models.ErrorResponse{
		Error: message,
	}
	writeJSONResponse(w, errorResp, statusCode)
}

// ValidateGenerateRequest validates a generate request
func ValidateGenerateRequest(req models.GenerateRequest) error {
	if strings.TrimSpace(req.Model) == "" {
		return fmt.Errorf("model is required")
	}

	if strings.TrimSpace(req.Prompt) == "" {
		return fmt.Errorf("prompt is required")
	}

	return nil
}

// ValidateChatRequest validates a chat request
func ValidateChatRequest(req models.ChatRequest) error {
	if strings.TrimSpace(req.Model) == "" {
		return fmt.Errorf("model is required")
	}

	if len(req.Messages) == 0 {
		return fmt.Errorf("messages is required and cannot be empty")
	}

	for i, msg := range req.Messages {
		if strings.TrimSpace(msg.Role) == "" {
			return fmt.Errorf("message %d: role is required", i)
		}

		if strings.TrimSpace(msg.Content) == "" {
			return fmt.Errorf("message %d: content is required", i)
		}

		// Validate role values
		if msg.Role != "user" && msg.Role != "assistant" && msg.Role != "system" {
			return fmt.Errorf("message %d: invalid role '%s', must be 'user', 'assistant', or 'system'", i, msg.Role)
		}
	}

	return nil
}

// ValidatePullRequest validates a pull request
func ValidatePullRequest(req models.PullRequest) error {
	if strings.TrimSpace(req.Name) == "" {
		return fmt.Errorf("name is required")
	}

	return nil
}

// ValidateShowRequest validates a show request
func ValidateShowRequest(req models.ShowRequest) error {
	if strings.TrimSpace(req.Name) == "" {
		return fmt.Errorf("name is required")
	}

	return nil
}

// ValidateBatchRequest validates a batch request
func ValidateBatchRequest(req models.BatchRequest) error {
	if len(req.Requests) == 0 {
		return fmt.Errorf("requests is required and cannot be empty")
	}

	if len(req.Requests) > 100 {
		return fmt.Errorf("too many requests, maximum is 100")
	}

	for i, item := range req.Requests {
		if strings.TrimSpace(item.ID) == "" {
			return fmt.Errorf("request %d: id is required", i)
		}

		if item.Type != "generate" && item.Type != "chat" {
			return fmt.Errorf("request %d: invalid type '%s', must be 'generate' or 'chat'", i, item.Type)
		}

		if item.Payload == nil {
			return fmt.Errorf("request %d: payload is required", i)
		}
	}

	return nil
}
