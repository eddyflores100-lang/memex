// Package memex provides a Go client SDK for Memex — local-first, zero-LLM agent memory.
//
// Usage:
//
//	client := memex.New("http://127.0.0.1:19420", "")
//	client.Store("We decided to use JWT with 3600s expiry.")
//	result, _ := client.Recall("what did we decide about auth")
//	for _, m := range result.Memories {
//	    fmt.Println(m.Text)
//	}
package memex

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

// DefaultURL is the default Memex server URL.
const DefaultURL = "http://127.0.0.1:19420"

// Client is the Memex API client.
type Client struct {
	BaseURL  string
	APIToken string
	Timeout  time.Duration
	http     *http.Client
}

// Memory represents a single memory record.
type Memory struct {
	Text     string                 `json:"text"`
	Score    float64                 `json:"score,omitempty"`
	ID       string                 `json:"id,omitempty"`
	Metadata map[string]interface{} `json:"metadata,omitempty"`
}

// RecallResult is the response from /recall.
type RecallResult struct {
	Memories []Memory `json:"memories"`
	Method   string   `json:"method"`
}

// HealthStatus is the response from /health.
type HealthStatus struct {
	Status     string `json:"status"`
	Count      int    `json:"count"`
	Queued     int    `json:"queued"`
	Version    string `json:"version"`
	Calibrated bool   `json:"calibrated"`
	Snapshot   bool   `json:"snapshot"`
}

// StoreResult is the response from /store.
type StoreResult struct {
	ID   string `json:"id"`
	Text string `json:"text"`
}

// New creates a new Memex client.
// baseURL: server URL (default: http://127.0.0.1:19420)
// apiToken: bearer token (empty = no auth)
func New(baseURL, apiToken string) *Client {
	if baseURL == "" {
		baseURL = DefaultURL
	}
	return &Client{
		BaseURL:  baseURL,
		APIToken: apiToken,
		Timeout:  30 * time.Second,
		http:     &http.Client{Timeout: 30 * time.Second},
	}
}

func (c *Client) do(method, path string, body interface{}) ([]byte, error) {
	var bodyReader io.Reader
	if body != nil {
		data, err := json.Marshal(body)
		if err != nil {
			return nil, fmt.Errorf("marshal error: %w", err)
		}
		bodyReader = bytes.NewReader(data)
	}

	req, err := http.NewRequest(method, c.BaseURL+path, bodyReader)
	if err != nil {
		return nil, fmt.Errorf("request error: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	if c.APIToken != "" {
		req.Header.Set("Authorization", "Bearer "+c.APIToken)
	}

	resp, err := c.http.Do(req)
	if err != nil {
		return nil, fmt.Errorf("connection error: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read error: %w", err)
	}

	if resp.StatusCode >= 400 {
		return nil, fmt.Errorf("HTTP %d: %s", resp.StatusCode, string(respBody))
	}

	return respBody, nil
}

// Health checks server health.
func (c *Client) Health() (*HealthStatus, error) {
	data, err := c.do("GET", "/health", nil)
	if err != nil {
		return nil, err
	}
	var h HealthStatus
	if err := json.Unmarshal(data, &h); err != nil {
		return nil, fmt.Errorf("parse error: %w", err)
	}
	return &h, nil
}

// Store stores a memory verbatim. No LLM call.
func (c *Client) Store(text string) (*StoreResult, error) {
	body := map[string]string{"text": text}
	data, err := c.do("POST", "/store", body)
	if err != nil {
		return nil, err
	}
	var r StoreResult
	if err := json.Unmarshal(data, &r); err != nil {
		return nil, fmt.Errorf("parse error: %w", err)
	}
	return &r, nil
}

// Recall retrieves memories for a query. Zero-LLM by default.
func (c *Client) Recall(query string, limit int) (*RecallResult, error) {
	if limit == 0 {
		limit = 50
	}
	body := map[string]interface{}{"text": query, "limit": limit}
	data, err := c.do("POST", "/recall", body)
	if err != nil {
		return nil, err
	}
	var r RecallResult
	if err := json.Unmarshal(data, &r); err != nil {
		return nil, fmt.Errorf("parse error: %w", err)
	}
	return &r, nil
}

// Query performs a simple vector search (no filter, no LLM).
func (c *Client) Query(query string, limit int) (*RecallResult, error) {
	if limit == 0 {
		limit = 5
	}
	body := map[string]interface{}{"text": query, "limit": limit}
	data, err := c.do("POST", "/query", body)
	if err != nil {
		return nil, err
	}
	var r RecallResult
	if err := json.Unmarshal(data, &r); err != nil {
		return nil, fmt.Errorf("parse error: %w", err)
	}
	return &r, nil
}

// Export exports all memories as JSON.
func (c *Client) Export() (map[string]interface{}, error) {
	data, err := c.do("GET", "/export", nil)
	if err != nil {
		return nil, err
	}
	var r map[string]interface{}
	if err := json.Unmarshal(data, &r); err != nil {
		return nil, fmt.Errorf("parse error: %w", err)
	}
	return r, nil
}
