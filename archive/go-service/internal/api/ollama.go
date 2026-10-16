package api

import (
	"encoding/json"
	"net/http"
	"time"

	"go-service/internal/logging"
	"go-service/internal/models"
	"go-service/internal/ollama"
)

// OllamaHandler wraps the Ollama client for HTTP handlers
type OllamaHandler struct {
	client *ollama.Client
	logger *logging.Logger
}

// NewOllamaHandler creates a new Ollama handler
func NewOllamaHandler() *OllamaHandler {
	return &OllamaHandler{
		client: ollama.NewClient(),
		logger: logging.NewDefaultLogger(),
	}
}

// NewOllamaHandlerWithLogger creates a new Ollama handler with custom logger
func NewOllamaHandlerWithLogger(logger *logging.Logger) *OllamaHandler {
	return &OllamaHandler{
		client: ollama.NewClient(),
		logger: logger,
	}
}

// HandleGenerate handles POST /api/generate requests
func (h *OllamaHandler) HandleGenerate(w http.ResponseWriter, r *http.Request) {
	start := time.Now()
	contextLogger := logging.LogWithContext(r.Context(), h.logger.Logger)

	contextLogger.Info("Generate request started",
		"component", "api.ollama",
		"endpoint", "/api/generate",
		"method", r.Method)

	if r.Method != http.MethodPost {
		contextLogger.Warn("Invalid method for generate endpoint",
			"component", "api.ollama",
			"method", r.Method,
			"expected", "POST")
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req models.GenerateRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		contextLogger.Error("Failed to decode generate request",
			"component", "api.ollama",
			"error", err.Error())
		writeErrorResponse(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	// Validate the request before calling the client
	if err := ValidateGenerateRequest(req); err != nil {
		contextLogger.Error("Generate request validation failed",
			"component", "api.ollama",
			"error", err.Error(),
			"model", req.Model)
		writeErrorResponse(w, err.Error(), http.StatusBadRequest)
		return
	}

	contextLogger.Info("Processing generate request",
		"component", "api.ollama",
		"model", req.Model,
		"prompt_length", len(req.Prompt))

	response, err := h.client.Generate(r.Context(), req)
	if err != nil {
		duration := time.Since(start)
		contextLogger.Error("Generate request failed",
			"component", "api.ollama",
			"error", err.Error(),
			"model", req.Model,
			"duration_ms", duration.Milliseconds())
		writeErrorResponse(w, err.Error(), http.StatusInternalServerError)
		return
	}

	duration := time.Since(start)
	contextLogger.Info("Generate request completed successfully",
		"component", "api.ollama",
		"model", req.Model,
		"duration_ms", duration.Milliseconds(),
		"response_length", len(response.Response))

	writeJSONResponse(w, response, http.StatusOK)
}

// HandleChat handles POST /api/chat requests
func (h *OllamaHandler) HandleChat(w http.ResponseWriter, r *http.Request) {
	start := time.Now()
	contextLogger := logging.LogWithContext(r.Context(), h.logger.Logger)

	contextLogger.Info("Chat request started",
		"component", "api.ollama",
		"endpoint", "/api/chat",
		"method", r.Method)

	if r.Method != http.MethodPost {
		contextLogger.Warn("Invalid method for chat endpoint",
			"component", "api.ollama",
			"method", r.Method,
			"expected", "POST")
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req models.ChatRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		contextLogger.Error("Failed to decode chat request",
			"component", "api.ollama",
			"error", err.Error())
		writeErrorResponse(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	// Validate the request before calling the client
	if err := ValidateChatRequest(req); err != nil {
		contextLogger.Error("Chat request validation failed",
			"component", "api.ollama",
			"error", err.Error(),
			"model", req.Model,
			"message_count", len(req.Messages))
		writeErrorResponse(w, err.Error(), http.StatusBadRequest)
		return
	}

	contextLogger.Info("Processing chat request",
		"component", "api.ollama",
		"model", req.Model,
		"message_count", len(req.Messages))

	response, err := h.client.Chat(r.Context(), req)
	if err != nil {
		duration := time.Since(start)
		contextLogger.Error("Chat request failed",
			"component", "api.ollama",
			"error", err.Error(),
			"model", req.Model,
			"duration_ms", duration.Milliseconds())
		writeErrorResponse(w, err.Error(), http.StatusInternalServerError)
		return
	}

	duration := time.Since(start)
	contextLogger.Info("Chat request completed successfully",
		"component", "api.ollama",
		"model", req.Model,
		"duration_ms", duration.Milliseconds(),
		"response_length", len(response.Message.Content))

	writeJSONResponse(w, response, http.StatusOK)
}

// HandleTags handles GET /api/tags requests
func (h *OllamaHandler) HandleTags(w http.ResponseWriter, r *http.Request) {
	start := time.Now()
	contextLogger := logging.LogWithContext(r.Context(), h.logger.Logger)

	contextLogger.Info("List models request started",
		"component", "api.ollama",
		"endpoint", "/api/tags",
		"method", r.Method)

	if r.Method != http.MethodGet {
		contextLogger.Warn("Invalid method for tags endpoint",
			"component", "api.ollama",
			"method", r.Method,
			"expected", "GET")
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	response, err := h.client.ListModels(r.Context())
	if err != nil {
		duration := time.Since(start)
		contextLogger.Error("List models request failed",
			"component", "api.ollama",
			"error", err.Error(),
			"duration_ms", duration.Milliseconds())
		writeErrorResponse(w, err.Error(), http.StatusInternalServerError)
		return
	}

	duration := time.Since(start)
	modelCount := 0
	if response.Models != nil {
		modelCount = len(response.Models)
	}

	contextLogger.Info("List models request completed successfully",
		"component", "api.ollama",
		"duration_ms", duration.Milliseconds(),
		"model_count", modelCount)

	writeJSONResponse(w, response, http.StatusOK)
}

// HandlePull handles POST /api/pull requests
func (h *OllamaHandler) HandlePull(w http.ResponseWriter, r *http.Request) {
	start := time.Now()
	contextLogger := logging.LogWithContext(r.Context(), h.logger.Logger)

	contextLogger.Info("Pull model request started",
		"component", "api.ollama",
		"endpoint", "/api/pull",
		"method", r.Method)

	if r.Method != http.MethodPost {
		contextLogger.Warn("Invalid method for pull endpoint",
			"component", "api.ollama",
			"method", r.Method,
			"expected", "POST")
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req models.PullRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		contextLogger.Error("Failed to decode pull request",
			"component", "api.ollama",
			"error", err.Error())
		writeErrorResponse(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	contextLogger.Info("Processing pull model request",
		"component", "api.ollama",
		"model_name", req.Name)

	err := h.client.PullModel(r.Context(), req)
	if err != nil {
		duration := time.Since(start)
		contextLogger.Error("Pull model request failed",
			"component", "api.ollama",
			"error", err.Error(),
			"model_name", req.Name,
			"duration_ms", duration.Milliseconds())
		writeErrorResponse(w, err.Error(), http.StatusInternalServerError)
		return
	}

	duration := time.Since(start)
	contextLogger.Info("Pull model request completed successfully",
		"component", "api.ollama",
		"model_name", req.Name,
		"duration_ms", duration.Milliseconds())

	// For pull operations, return a simple success response
	writeJSONResponse(w, map[string]string{"status": "success"}, http.StatusOK)
}

// HandleShow handles POST /api/show requests
func (h *OllamaHandler) HandleShow(w http.ResponseWriter, r *http.Request) {
	start := time.Now()
	contextLogger := logging.LogWithContext(r.Context(), h.logger.Logger)

	contextLogger.Info("Show model request started",
		"component", "api.ollama",
		"endpoint", "/api/show",
		"method", r.Method)

	if r.Method != http.MethodPost {
		contextLogger.Warn("Invalid method for show endpoint",
			"component", "api.ollama",
			"method", r.Method,
			"expected", "POST")
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req models.ShowRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		contextLogger.Error("Failed to decode show request",
			"component", "api.ollama",
			"error", err.Error())
		writeErrorResponse(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	contextLogger.Info("Processing show model request",
		"component", "api.ollama",
		"model_name", req.Name)

	response, err := h.client.ShowModel(r.Context(), req)
	if err != nil {
		duration := time.Since(start)
		contextLogger.Error("Show model request failed",
			"component", "api.ollama",
			"error", err.Error(),
			"model_name", req.Name,
			"duration_ms", duration.Milliseconds())
		writeErrorResponse(w, err.Error(), http.StatusInternalServerError)
		return
	}

	duration := time.Since(start)
	contextLogger.Info("Show model request completed successfully",
		"component", "api.ollama",
		"model_name", req.Name,
		"duration_ms", duration.Milliseconds())

	writeJSONResponse(w, response, http.StatusOK)
}

// HandlePS handles GET /api/ps requests (running models status)
func (h *OllamaHandler) HandlePS(w http.ResponseWriter, r *http.Request) {
	start := time.Now()
	contextLogger := logging.LogWithContext(r.Context(), h.logger.Logger)

	contextLogger.Info("Process status request started",
		"component", "api.ollama",
		"endpoint", "/api/ps",
		"method", r.Method)

	if r.Method != http.MethodGet {
		contextLogger.Warn("Invalid method for ps endpoint",
			"component", "api.ollama",
			"method", r.Method,
			"expected", "GET")
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// For now, return empty list since this is primarily for status
	// In a real implementation, this would check actual running models
	response := map[string]interface{}{
		"models": []interface{}{},
	}

	duration := time.Since(start)
	contextLogger.Info("Process status request completed successfully",
		"component", "api.ollama",
		"duration_ms", duration.Milliseconds(),
		"running_models", 0)

	writeJSONResponse(w, response, http.StatusOK)
}
