package ollama

import (
	"sync"
	"time"
)

// Pool manages connection pooling for the Ollama client
type Pool struct {
	size      int
	active    int
	available chan struct{}
	mu        sync.Mutex
}

// NewPool creates a new connection pool with the specified size
func NewPool(size int) *Pool {
	pool := &Pool{
		size:      size,
		available: make(chan struct{}, size),
	}

	// Fill the pool with available slots
	for i := 0; i < size; i++ {
		pool.available <- struct{}{}
	}

	return pool
}

// Acquire gets a connection from the pool, blocking if none are available
func (p *Pool) Acquire() {
	<-p.available
	p.mu.Lock()
	p.active++
	p.mu.Unlock()
}

// Release returns a connection to the pool
func (p *Pool) Release() {
	p.mu.Lock()
	if p.active > 0 {
		p.active--
	}
	p.mu.Unlock()

	select {
	case p.available <- struct{}{}:
	default:
		// Pool is full, this shouldn't happen but handle gracefully
	}
}

// AcquireTimeout attempts to acquire a connection with a timeout
func (p *Pool) AcquireTimeout(timeout time.Duration) bool {
	select {
	case <-p.available:
		p.mu.Lock()
		p.active++
		p.mu.Unlock()
		return true
	case <-time.After(timeout):
		return false
	}
}

// Stats returns current pool statistics
func (p *Pool) Stats() (available, active, total int) {
	p.mu.Lock()
	defer p.mu.Unlock()

	return len(p.available), p.active, p.size
}
