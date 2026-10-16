package api

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strings"

	"go-service/internal/models"
)

// HandleModels handles GET /api/models requests (enhanced model listing)
func (h *OllamaHandler) HandleModels(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Get basic model list from Ollama
	tagsResponse, err := h.client.ListModels(r.Context())
	if err != nil {
		writeErrorResponse(w, err.Error(), http.StatusInternalServerError)
		return
	}

	// Enhanced response with additional metadata
	enhancedResponse := map[string]interface{}{
		"models":      tagsResponse.Models,
		"total_count": len(tagsResponse.Models),
		"service":     "ollama-proxy",
		"version":     "1.0.0",
	}

	writeJSONResponse(w, enhancedResponse, http.StatusOK)
}

// HandleModelInfo handles GET /api/models/{model}/info requests
func (h *OllamaHandler) HandleModelInfo(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Extract model name from URL path
	modelName := extractModelFromPath(r.URL.Path)
	if modelName == "" {
		writeErrorResponse(w, "Model name is required", http.StatusBadRequest)
		return
	}

	// Get detailed model information
	showReq := models.ShowRequest{Name: modelName}
	showResponse, err := h.client.ShowModel(r.Context(), showReq)
	if err != nil {
		writeErrorResponse(w, err.Error(), http.StatusInternalServerError)
		return
	}

	// Get basic model info from tags
	tagsResponse, err := h.client.ListModels(r.Context())
	if err != nil {
		writeErrorResponse(w, err.Error(), http.StatusInternalServerError)
		return
	}

	// Find the specific model in the tags response
	var modelInfo *models.ModelInfo
	for _, model := range tagsResponse.Models {
		if model.Name == modelName {
			modelInfo = &model
			break
		}
	}

	// Enhanced response combining show and tags data
	enhancedResponse := map[string]interface{}{
		"name":       modelName,
		"license":    showResponse.License,
		"modelfile":  showResponse.Modelfile,
		"parameters": showResponse.Parameters,
		"template":   showResponse.Template,
		"details":    showResponse.Details,
	}

	if modelInfo != nil {
		enhancedResponse["size"] = modelInfo.Size
		enhancedResponse["modified_at"] = modelInfo.ModifiedAt
		enhancedResponse["digest"] = modelInfo.Digest
	}

	writeJSONResponse(w, enhancedResponse, http.StatusOK)
}

// HandleBatch handles POST /api/batch requests
func (h *OllamaHandler) HandleBatch(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req models.BatchRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeErrorResponse(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	if err := ValidateBatchRequest(req); err != nil {
		writeErrorResponse(w, err.Error(), http.StatusBadRequest)
		return
	}

	// Process batch requests
	results := make([]models.BatchResult, len(req.Requests))

	for i, item := range req.Requests {
		result := models.BatchResult{
			ID: item.ID,
		}

		switch item.Type {
		case "generate":
			result = h.processBatchGenerate(r, item)
		case "chat":
			result = h.processBatchChat(r, item)
		default:
			result.Status = "error"
			result.Error = fmt.Sprintf("Unknown request type: %s", item.Type)
		}

		results[i] = result
	}

	response := models.BatchResponse{
		Results: results,
	}

	writeJSONResponse(w, response, http.StatusOK)
}

// processBatchGenerate processes a single generate request in a batch
func (h *OllamaHandler) processBatchGenerate(r *http.Request, item models.BatchItem) models.BatchResult {
	result := models.BatchResult{ID: item.ID}

	// Convert payload to GenerateRequest
	payloadBytes, err := json.Marshal(item.Payload)
	if err != nil {
		result.Status = "error"
		result.Error = "Failed to marshal payload"
		return result
	}

	var genReq models.GenerateRequest
	if err := json.Unmarshal(payloadBytes, &genReq); err != nil {
		result.Status = "error"
		result.Error = "Invalid generate request payload"
		return result
	}

	if err := ValidateGenerateRequest(genReq); err != nil {
		result.Status = "error"
		result.Error = err.Error()
		return result
	}

	response, err := h.client.Generate(r.Context(), genReq)
	if err != nil {
		result.Status = "error"
		result.Error = err.Error()
		return result
	}

	result.Status = "success"
	result.Result = response
	return result
}

// processBatchChat processes a single chat request in a batch
func (h *OllamaHandler) processBatchChat(r *http.Request, item models.BatchItem) models.BatchResult {
	result := models.BatchResult{ID: item.ID}

	// Convert payload to ChatRequest
	payloadBytes, err := json.Marshal(item.Payload)
	if err != nil {
		result.Status = "error"
		result.Error = "Failed to marshal payload"
		return result
	}

	var chatReq models.ChatRequest
	if err := json.Unmarshal(payloadBytes, &chatReq); err != nil {
		result.Status = "error"
		result.Error = "Invalid chat request payload"
		return result
	}

	if err := ValidateChatRequest(chatReq); err != nil {
		result.Status = "error"
		result.Error = err.Error()
		return result
	}

	response, err := h.client.Chat(r.Context(), chatReq)
	if err != nil {
		result.Status = "error"
		result.Error = err.Error()
		return result
	}

	result.Status = "success"
	result.Result = response
	return result
}

// extractModelFromPath extracts model name from URL path like /api/models/{model}/info
func extractModelFromPath(urlPath string) string {
	// Remove leading/trailing slashes and split
	urlPath = strings.Trim(urlPath, "/")
	parts := strings.Split(urlPath, "/")

	// Expected format: api/models/{model}/info
	if len(parts) >= 3 && parts[0] == "api" && parts[1] == "models" {
		return parts[2]
	}

	return ""
}

// HandleHealth handles GET /health requests
func (h *OllamaHandler) HandleHealth(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Check if we can connect to Ollama
	err := h.client.HealthCheck(r.Context())

	response := models.HealthResponse{
		Status: "healthy",
	}

	if err != nil {
		response.Status = "unhealthy"
		writeJSONResponse(w, response, http.StatusServiceUnavailable)
		return
	}

	response.Status = "healthy"
	writeJSONResponse(w, response, http.StatusOK)
}
