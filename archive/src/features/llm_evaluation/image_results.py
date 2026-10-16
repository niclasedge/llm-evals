import json
import sqlite3
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ImageGenerationResults:
    """Handles storage and retrieval of image generation results"""
    
    def __init__(self, db_path: str = "image_evaluation_results.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize the SQLite database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS evaluation_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    config TEXT,
                    summary TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create generations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS image_generations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    prompt_category TEXT,
                    prompt_complexity TEXT,
                    success BOOLEAN NOT NULL,
                    error_message TEXT,
                    filepath TEXT,
                    filename TEXT,
                    size TEXT,
                    quality TEXT,
                    generation_time REAL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES evaluation_sessions (session_id)
                )
            """)
            
            # Create indexes for better query performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_generations_session 
                ON image_generations(session_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_generations_provider_model 
                ON image_generations(provider, model)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_generations_category 
                ON image_generations(prompt_category)
            """)
            
            conn.commit()
    
    async def save_session(self, session_data: Dict[str, Any]) -> None:
        """Save evaluation session data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Save session
                cursor.execute("""
                    INSERT OR REPLACE INTO evaluation_sessions 
                    (session_id, start_time, end_time, config, summary)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    session_data["session_id"],
                    session_data["start_time"],
                    session_data.get("end_time"),
                    json.dumps(session_data.get("config", {})),
                    json.dumps(session_data.get("summary", {}))
                ))
                
                # Save individual generations
                for provider, provider_data in session_data.get("results", {}).items():
                    for model, model_data in provider_data.get("models", {}).items():
                        for generation in model_data.get("generations", []):
                            await self._save_generation(
                                session_data["session_id"],
                                provider,
                                model,
                                generation
                            )
                
                conn.commit()
                logger.info(f"Session {session_data['session_id']} saved to database")
                
        except Exception as e:
            logger.error(f"Error saving session to database: {e}")
            raise
    
    async def _save_generation(self, session_id: str, provider: str, model: str, 
                             generation: Dict[str, Any]) -> None:
        """Save individual generation result"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                prompt_metadata = generation.get("prompt_metadata", {})
                
                cursor.execute("""
                    INSERT INTO image_generations 
                    (session_id, provider, model, prompt, prompt_category, prompt_complexity,
                     success, error_message, filepath, filename, size, quality, 
                     generation_time, timestamp, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    provider,
                    model,
                    generation.get("prompt", ""),
                    prompt_metadata.get("category"),
                    prompt_metadata.get("complexity"),
                    generation.get("success", False),
                    generation.get("error"),
                    generation.get("filepath"),
                    generation.get("filename"),
                    generation.get("size"),
                    generation.get("quality"),
                    generation.get("generation_time"),
                    generation.get("timestamp", datetime.now().isoformat()),
                    json.dumps(generation)
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error saving generation to database: {e}")
            raise
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session data by session ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT session_id, start_time, end_time, config, summary
                    FROM evaluation_sessions
                    WHERE session_id = ?
                """, (session_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                session_data = {
                    "session_id": row[0],
                    "start_time": row[1],
                    "end_time": row[2],
                    "config": json.loads(row[3]) if row[3] else {},
                    "summary": json.loads(row[4]) if row[4] else {}
                }
                
                # Get generations for this session
                cursor.execute("""
                    SELECT * FROM image_generations
                    WHERE session_id = ?
                    ORDER BY created_at
                """, (session_id,))
                
                generations = []
                for gen_row in cursor.fetchall():
                    generations.append({
                        "id": gen_row[0],
                        "session_id": gen_row[1],
                        "provider": gen_row[2],
                        "model": gen_row[3],
                        "prompt": gen_row[4],
                        "prompt_category": gen_row[5],
                        "prompt_complexity": gen_row[6],
                        "success": bool(gen_row[7]),
                        "error_message": gen_row[8],
                        "filepath": gen_row[9],
                        "filename": gen_row[10],
                        "size": gen_row[11],
                        "quality": gen_row[12],
                        "generation_time": gen_row[13],
                        "timestamp": gen_row[14],
                        "metadata": json.loads(gen_row[15]) if gen_row[15] else {},
                        "created_at": gen_row[16]
                    })
                
                session_data["generations"] = generations
                return session_data
                
        except Exception as e:
            logger.error(f"Error retrieving session {session_id}: {e}")
            return None
    
    def get_recent_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent evaluation sessions"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT session_id, start_time, end_time, config, summary
                    FROM evaluation_sessions
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))
                
                sessions = []
                for row in cursor.fetchall():
                    sessions.append({
                        "session_id": row[0],
                        "start_time": row[1],
                        "end_time": row[2],
                        "config": json.loads(row[3]) if row[3] else {},
                        "summary": json.loads(row[4]) if row[4] else {}
                    })
                
                return sessions
                
        except Exception as e:
            logger.error(f"Error retrieving recent sessions: {e}")
            return []
    
    def get_provider_statistics(self, provider: str = None) -> Dict[str, Any]:
        """Get statistics for a specific provider or all providers"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if provider:
                    where_clause = "WHERE provider = ?"
                    params = (provider,)
                else:
                    where_clause = ""
                    params = ()
                
                # Get basic statistics
                cursor.execute(f"""
                    SELECT 
                        provider,
                        model,
                        COUNT(*) as total_generations,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_generations,
                        AVG(CASE WHEN success = 1 THEN generation_time END) as avg_generation_time,
                        MIN(CASE WHEN success = 1 THEN generation_time END) as min_generation_time,
                        MAX(CASE WHEN success = 1 THEN generation_time END) as max_generation_time
                    FROM image_generations
                    {where_clause}
                    GROUP BY provider, model
                    ORDER BY provider, model
                """, params)
                
                stats = []
                for row in cursor.fetchall():
                    stats.append({
                        "provider": row[0],
                        "model": row[1],
                        "total_generations": row[2],
                        "successful_generations": row[3],
                        "success_rate": row[3] / row[2] if row[2] > 0 else 0,
                        "avg_generation_time": row[4],
                        "min_generation_time": row[5],
                        "max_generation_time": row[6]
                    })
                
                return {"statistics": stats}
                
        except Exception as e:
            logger.error(f"Error retrieving provider statistics: {e}")
            return {"statistics": []}
    
    def get_category_performance(self) -> Dict[str, Any]:
        """Get performance statistics by prompt category"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT 
                        prompt_category,
                        prompt_complexity,
                        COUNT(*) as total_generations,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_generations,
                        AVG(CASE WHEN success = 1 THEN generation_time END) as avg_generation_time
                    FROM image_generations
                    WHERE prompt_category IS NOT NULL
                    GROUP BY prompt_category, prompt_complexity
                    ORDER BY prompt_category, prompt_complexity
                """)
                
                performance = {}
                for row in cursor.fetchall():
                    category = row[0]
                    complexity = row[1]
                    
                    if category not in performance:
                        performance[category] = {}
                    
                    performance[category][complexity] = {
                        "total_generations": row[2],
                        "successful_generations": row[3],
                        "success_rate": row[3] / row[2] if row[2] > 0 else 0,
                        "avg_generation_time": row[4]
                    }
                
                return performance
                
        except Exception as e:
            logger.error(f"Error retrieving category performance: {e}")
            return {}
    
    def export_results(self, output_file: str, format: str = "json") -> None:
        """Export all results to a file"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get all sessions
                cursor.execute("""
                    SELECT session_id, start_time, end_time, config, summary
                    FROM evaluation_sessions
                    ORDER BY created_at DESC
                """)
                
                sessions = []
                for row in cursor.fetchall():
                    session_data = {
                        "session_id": row[0],
                        "start_time": row[1],
                        "end_time": row[2],
                        "config": json.loads(row[3]) if row[3] else {},
                        "summary": json.loads(row[4]) if row[4] else {}
                    }
                    
                    # Get generations for this session
                    cursor.execute("""
                        SELECT * FROM image_generations
                        WHERE session_id = ?
                        ORDER BY created_at
                    """, (row[0],))
                    
                    generations = []
                    for gen_row in cursor.fetchall():
                        generations.append({
                            "provider": gen_row[2],
                            "model": gen_row[3],
                            "prompt": gen_row[4],
                            "prompt_category": gen_row[5],
                            "prompt_complexity": gen_row[6],
                            "success": bool(gen_row[7]),
                            "error_message": gen_row[8],
                            "filepath": gen_row[9],
                            "filename": gen_row[10],
                            "size": gen_row[11],
                            "quality": gen_row[12],
                            "generation_time": gen_row[13],
                            "timestamp": gen_row[14],
                            "metadata": json.loads(gen_row[15]) if gen_row[15] else {}
                        })
                    
                    session_data["generations"] = generations
                    sessions.append(session_data)
                
                # Export data
                export_data = {
                    "export_timestamp": datetime.now().isoformat(),
                    "total_sessions": len(sessions),
                    "sessions": sessions
                }
                
                if format.lower() == "json":
                    with open(output_file, "w") as f:
                        json.dump(export_data, f, indent=2, default=str)
                else:
                    raise ValueError(f"Unsupported export format: {format}")
                
                logger.info(f"Results exported to {output_file}")
                
        except Exception as e:
            logger.error(f"Error exporting results: {e}")
            raise
    
    def cleanup_old_results(self, days_old: int = 30) -> None:
        """Clean up old results from the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Delete old sessions and their generations
                cursor.execute("""
                    DELETE FROM evaluation_sessions
                    WHERE created_at < datetime('now', '-{} days')
                """.format(days_old))
                
                cursor.execute("""
                    DELETE FROM image_generations
                    WHERE created_at < datetime('now', '-{} days')
                """.format(days_old))
                
                conn.commit()
                logger.info(f"Cleaned up results older than {days_old} days")
                
        except Exception as e:
            logger.error(f"Error cleaning up old results: {e}")
            raise