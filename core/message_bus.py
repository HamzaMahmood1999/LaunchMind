"""
Message Bus — LaunchMind Core

A SQLite-backed message bus that enforces the strict JSON communication
protocol between all agents in the LaunchMind multi-agent system.

Every message must conform to the AgentMessage schema:
    - message_id:        Unique UUID string
    - from_agent:        Sender agent name
    - to_agent:          Recipient agent name
    - message_type:      One of 'task', 'result', 'revision_request', 'confirmation'
    - payload:           Arbitrary JSON-serializable dict
    - timestamp:         ISO 8601 datetime string
    - parent_message_id: Optional reference to a parent message (for threads)

The bus is thread-safe via SQLite's built-in locking and supports:
    - send()           → Insert a validated message into the store
    - receive()        → Fetch unread messages for a specific agent
    - get_thread()     → Retrieve a full conversation thread
    - get_history()    → Return all messages for debugging / audit
    - create_message() → Helper to build a valid AgentMessage with auto-generated ID + timestamp
"""

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Message Schema
# ---------------------------------------------------------------------------

class MessageType(str, Enum):
    """Valid message types for inter-agent communication."""
    TASK = "task"
    RESULT = "result"
    REVISION_REQUEST = "revision_request"
    CONFIRMATION = "confirmation"


class AgentMessage(BaseModel):
    """
    Pydantic model enforcing the strict 7-field JSON communication protocol.

    All fields are validated at construction time. Invalid messages will
    raise a ValidationError before they ever reach the bus.
    """
    message_id: str = Field(
        ..., description="Unique identifier for this message (UUID4)."
    )
    from_agent: str = Field(
        ..., description="Name of the sending agent."
    )
    to_agent: str = Field(
        ..., description="Name of the receiving agent."
    )
    message_type: MessageType = Field(
        ..., description="Type of message: task, result, revision_request, or confirmation."
    )
    payload: dict[str, Any] = Field(
        ..., description="Arbitrary JSON-serializable payload."
    )
    timestamp: str = Field(
        ..., description="ISO 8601 formatted timestamp."
    )
    parent_message_id: Optional[str] = Field(
        default=None,
        description="Optional reference to a parent message for threading.",
    )

    @field_validator("from_agent", "to_agent")
    @classmethod
    def agent_name_must_be_nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Agent name must be a non-empty string.")
        return v.strip().lower()

    @field_validator("timestamp")
    @classmethod
    def timestamp_must_be_iso8601(cls, v: str) -> str:
        try:
            datetime.fromisoformat(v)
        except ValueError:
            raise ValueError(f"Timestamp must be ISO 8601 format, got: {v}")
        return v

    def to_dict(self) -> dict:
        """Serialize to a plain dict (JSON-friendly)."""
        return self.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Message Bus
# ---------------------------------------------------------------------------

class MessageBus:
    """
    SQLite-backed message bus for inter-agent communication.

    Provides persistent, thread-safe message passing with full audit
    history. Each message is validated against AgentMessage before storage.

    Args:
        db_path: Path to SQLite database file. Use ':memory:' for testing.
    """

    def __init__(self, db_path: str = "messages.db"):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()
        logger.info(f"MessageBus initialized (db={db_path}).")

    def _create_tables(self) -> None:
        """Create the messages table if it doesn't exist."""
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id      TEXT UNIQUE NOT NULL,
                from_agent      TEXT NOT NULL,
                to_agent        TEXT NOT NULL,
                message_type    TEXT NOT NULL,
                payload         TEXT NOT NULL,
                timestamp       TEXT NOT NULL,
                parent_message_id TEXT,
                is_read         INTEGER DEFAULT 0
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_to_agent_unread
            ON messages (to_agent, is_read)
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_parent_message
            ON messages (parent_message_id)
        """)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_message(
        self,
        from_agent: str,
        to_agent: str,
        message_type: str,
        payload: dict[str, Any],
        parent_message_id: str | None = None,
    ) -> AgentMessage:
        """
        Factory method to create a validated AgentMessage with
        auto-generated message_id (UUID4) and timestamp (ISO 8601 UTC).

        Args:
            from_agent:        Sender agent name.
            to_agent:          Recipient agent name.
            message_type:      One of 'task', 'result', 'revision_request', 'confirmation'.
            payload:           Arbitrary JSON-serializable data.
            parent_message_id: Optional parent message ID for threading.

        Returns:
            A validated AgentMessage instance.

        Raises:
            pydantic.ValidationError: If any field fails validation.
        """
        return AgentMessage(
            message_id=str(uuid.uuid4()),
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            payload=payload,
            timestamp=datetime.now(timezone.utc).isoformat(),
            parent_message_id=parent_message_id,
        )

    def send(self, message: AgentMessage) -> None:
        """
        Send a message by inserting it into the SQLite store.

        The message is validated at construction time via Pydantic,
        so by the time it reaches here it is guaranteed to be well-formed.

        Args:
            message: A validated AgentMessage instance.
        """
        try:
            self._conn.execute(
                """
                INSERT INTO messages
                    (message_id, from_agent, to_agent, message_type,
                     payload, timestamp, parent_message_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message.message_id,
                    message.from_agent,
                    message.to_agent,
                    message.message_type.value,
                    json.dumps(message.payload),
                    message.timestamp,
                    message.parent_message_id,
                ),
            )
            self._conn.commit()
            logger.info(
                f"📤 Message sent: {message.from_agent} → {message.to_agent} "
                f"[{message.message_type.value}] (id={message.message_id[:8]}…)"
            )
        except sqlite3.IntegrityError:
            logger.warning(
                f"Duplicate message_id: {message.message_id}. Skipping."
            )

    def receive(self, agent_name: str) -> list[AgentMessage]:
        """
        Fetch all unread messages for the specified agent and mark them read.

        Args:
            agent_name: Name of the receiving agent.

        Returns:
            List of AgentMessage objects (may be empty).
        """
        agent_name = agent_name.strip().lower()
        cursor = self._conn.execute(
            """
            SELECT message_id, from_agent, to_agent, message_type,
                   payload, timestamp, parent_message_id
            FROM messages
            WHERE to_agent = ? AND is_read = 0
            ORDER BY id ASC
            """,
            (agent_name,),
        )
        rows = cursor.fetchall()
        messages = []
        for row in rows:
            msg = AgentMessage(
                message_id=row["message_id"],
                from_agent=row["from_agent"],
                to_agent=row["to_agent"],
                message_type=row["message_type"],
                payload=json.loads(row["payload"]),
                timestamp=row["timestamp"],
                parent_message_id=row["parent_message_id"],
            )
            messages.append(msg)

        # Mark all fetched messages as read
        if messages:
            ids = [m.message_id for m in messages]
            placeholders = ",".join("?" for _ in ids)
            self._conn.execute(
                f"UPDATE messages SET is_read = 1 WHERE message_id IN ({placeholders})",
                ids,
            )
            self._conn.commit()
            logger.info(
                f"📥 {agent_name} received {len(messages)} message(s)."
            )

        return messages

    def get_thread(self, parent_message_id: str) -> list[AgentMessage]:
        """
        Retrieve all messages in a thread (sharing the same parent_message_id).

        Args:
            parent_message_id: The parent message ID to trace the thread from.

        Returns:
            List of AgentMessage objects in chronological order.
        """
        cursor = self._conn.execute(
            """
            SELECT message_id, from_agent, to_agent, message_type,
                   payload, timestamp, parent_message_id
            FROM messages
            WHERE parent_message_id = ? OR message_id = ?
            ORDER BY id ASC
            """,
            (parent_message_id, parent_message_id),
        )
        return [
            AgentMessage(
                message_id=row["message_id"],
                from_agent=row["from_agent"],
                to_agent=row["to_agent"],
                message_type=row["message_type"],
                payload=json.loads(row["payload"]),
                timestamp=row["timestamp"],
                parent_message_id=row["parent_message_id"],
            )
            for row in cursor.fetchall()
        ]

    def get_history(self) -> list[AgentMessage]:
        """
        Return all messages ever sent through the bus (read + unread).

        Useful for debugging, auditing, and pipeline visualization.

        Returns:
            List of all AgentMessage objects in chronological order.
        """
        cursor = self._conn.execute(
            """
            SELECT message_id, from_agent, to_agent, message_type,
                   payload, timestamp, parent_message_id
            FROM messages
            ORDER BY id ASC
            """
        )
        return [
            AgentMessage(
                message_id=row["message_id"],
                from_agent=row["from_agent"],
                to_agent=row["to_agent"],
                message_type=row["message_type"],
                payload=json.loads(row["payload"]),
                timestamp=row["timestamp"],
                parent_message_id=row["parent_message_id"],
            )
            for row in cursor.fetchall()
        ]

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()
        logger.info("MessageBus connection closed.")
