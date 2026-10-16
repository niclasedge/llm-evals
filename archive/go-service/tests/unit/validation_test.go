package unit

import (
	"testing"

	"go-service/internal/api"
	"go-service/internal/models"
)

func TestValidateGenerateRequest(t *testing.T) {
	tests := []struct {
		name    string
		req     models.GenerateRequest
		wantErr bool
	}{
		{
			name: "valid request",
			req: models.GenerateRequest{
				Model:  "llama3.2:3b",
				Prompt: "Hello, world!",
				Stream: false,
			},
			wantErr: false,
		},
		{
			name: "missing model",
			req: models.GenerateRequest{
				Prompt: "Hello, world!",
				Stream: false,
			},
			wantErr: true,
		},
		{
			name: "missing prompt",
			req: models.GenerateRequest{
				Model:  "llama3.2:3b",
				Stream: false,
			},
			wantErr: true,
		},
		{
			name: "empty model",
			req: models.GenerateRequest{
				Model:  "   ",
				Prompt: "Hello, world!",
				Stream: false,
			},
			wantErr: true,
		},
		{
			name: "empty prompt",
			req: models.GenerateRequest{
				Model:  "llama3.2:3b",
				Prompt: "   ",
				Stream: false,
			},
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := api.ValidateGenerateRequest(tt.req)
			if (err != nil) != tt.wantErr {
				t.Errorf("ValidateGenerateRequest() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}

func TestValidateChatRequest(t *testing.T) {
	tests := []struct {
		name    string
		req     models.ChatRequest
		wantErr bool
	}{
		{
			name: "valid request",
			req: models.ChatRequest{
				Model: "llama3.2:3b",
				Messages: []models.ChatMessage{
					{Role: "user", Content: "Hello"},
					{Role: "assistant", Content: "Hi there!"},
				},
				Stream: false,
			},
			wantErr: false,
		},
		{
			name: "missing model",
			req: models.ChatRequest{
				Messages: []models.ChatMessage{
					{Role: "user", Content: "Hello"},
				},
				Stream: false,
			},
			wantErr: true,
		},
		{
			name: "empty messages",
			req: models.ChatRequest{
				Model:    "llama3.2:3b",
				Messages: []models.ChatMessage{},
				Stream:   false,
			},
			wantErr: true,
		},
		{
			name: "invalid role",
			req: models.ChatRequest{
				Model: "llama3.2:3b",
				Messages: []models.ChatMessage{
					{Role: "invalid", Content: "Hello"},
				},
				Stream: false,
			},
			wantErr: true,
		},
		{
			name: "empty content",
			req: models.ChatRequest{
				Model: "llama3.2:3b",
				Messages: []models.ChatMessage{
					{Role: "user", Content: ""},
				},
				Stream: false,
			},
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := api.ValidateChatRequest(tt.req)
			if (err != nil) != tt.wantErr {
				t.Errorf("ValidateChatRequest() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}

func TestValidateBatchRequest(t *testing.T) {
	tests := []struct {
		name    string
		req     models.BatchRequest
		wantErr bool
	}{
		{
			name: "valid batch request",
			req: models.BatchRequest{
				Requests: []models.BatchItem{
					{
						ID:   "1",
						Type: "generate",
						Payload: models.GenerateRequest{
							Model:  "llama3.2:3b",
							Prompt: "Hello",
						},
					},
					{
						ID:   "2",
						Type: "chat",
						Payload: models.ChatRequest{
							Model: "llama3.2:3b",
							Messages: []models.ChatMessage{
								{Role: "user", Content: "Hello"},
							},
						},
					},
				},
			},
			wantErr: false,
		},
		{
			name: "empty requests",
			req: models.BatchRequest{
				Requests: []models.BatchItem{},
			},
			wantErr: true,
		},
		{
			name: "missing id",
			req: models.BatchRequest{
				Requests: []models.BatchItem{
					{
						Type: "generate",
						Payload: models.GenerateRequest{
							Model:  "llama3.2:3b",
							Prompt: "Hello",
						},
					},
				},
			},
			wantErr: true,
		},
		{
			name: "invalid type",
			req: models.BatchRequest{
				Requests: []models.BatchItem{
					{
						ID:      "1",
						Type:    "invalid",
						Payload: nil,
					},
				},
			},
			wantErr: true,
		},
		{
			name: "missing payload",
			req: models.BatchRequest{
				Requests: []models.BatchItem{
					{
						ID:      "1",
						Type:    "generate",
						Payload: nil,
					},
				},
			},
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := api.ValidateBatchRequest(tt.req)
			if (err != nil) != tt.wantErr {
				t.Errorf("ValidateBatchRequest() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}
