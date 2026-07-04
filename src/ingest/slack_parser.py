"""
Slack/JSON thread parser for VaultIQ.
Parses Slack-like threaded conversations from JSON files.
"""

import json
import os
from . import BaseParser, Document


class SlackParser(BaseParser):
    """Parse Slack-like JSON thread files into Document chunks.

    Each thread becomes one document. Long threads (>10 messages) are split
    at message boundaries, with the parent message included in each chunk
    for context.
    """

    source_type = "slack"
    MAX_MESSAGES_PER_CHUNK = 10

    def parse(self, file_path: str) -> list[Document]:
        """Parse a JSON file containing Slack-like threads.

        Expects the JSON to be a list of thread objects, each with:
        - thread_id: str
        - channel: str
        - acl_roles: list[str]
        - messages: list[{user, timestamp, text}]

        Args:
            file_path: Path to the JSON file.

        Returns:
            List of Document objects, one per thread (or thread chunk).
        """
        with open(file_path, "r", encoding="utf-8") as f:
            threads = json.load(f)

        documents = []

        for thread in threads:
            thread_id = thread.get("thread_id", "unknown")
            channel = thread.get("channel", "#unknown")
            acl_roles = thread.get("acl_roles", ["all-employees"])
            messages = thread.get("messages", [])

            if not messages:
                continue

            # For short threads, create one document
            if len(messages) <= self.MAX_MESSAGES_PER_CHUNK:
                content = self._format_thread(messages, channel)
                title = self._generate_thread_title(messages, channel)

                doc = Document(
                    doc_id=self._generate_doc_id(file_path, hash(thread_id)),
                    content=content,
                    source_type=self.source_type,
                    source_file=os.path.basename(file_path),
                    title=title,
                    acl_roles=acl_roles,
                    metadata={
                        "thread_id": thread_id,
                        "channel": channel,
                        "message_count": len(messages),
                        "first_timestamp": messages[0].get("timestamp", ""),
                        "last_timestamp": messages[-1].get("timestamp", ""),
                        "participants": list(set(m.get("user", "") for m in messages)),
                    },
                )
                documents.append(doc)
            else:
                # Split long threads, keeping the parent message in each chunk
                parent_message = messages[0]
                remaining = messages[1:]

                for chunk_idx in range(0, len(remaining), self.MAX_MESSAGES_PER_CHUNK - 1):
                    chunk_messages = [parent_message] + remaining[
                        chunk_idx : chunk_idx + self.MAX_MESSAGES_PER_CHUNK - 1
                    ]
                    content = self._format_thread(chunk_messages, channel)
                    title = self._generate_thread_title(chunk_messages, channel)

                    doc = Document(
                        doc_id=self._generate_doc_id(
                            file_path, hash(f"{thread_id}_{chunk_idx}")
                        ),
                        content=content,
                        source_type=self.source_type,
                        source_file=os.path.basename(file_path),
                        title=title,
                        acl_roles=acl_roles,
                        metadata={
                            "thread_id": thread_id,
                            "channel": channel,
                            "chunk_index": chunk_idx,
                            "message_count": len(chunk_messages),
                            "participants": list(
                                set(m.get("user", "") for m in chunk_messages)
                            ),
                        },
                    )
                    documents.append(doc)

        return documents

    def _format_thread(self, messages: list[dict], channel: str) -> str:
        """Format a list of messages into a readable thread string."""
        lines = [f"Channel: {channel}", ""]
        for msg in messages:
            user = msg.get("user", "unknown")
            timestamp = msg.get("timestamp", "")
            text = msg.get("text", "")
            # Format timestamp to be more readable
            if "T" in timestamp:
                time_part = timestamp.split("T")[1][:5]
                date_part = timestamp.split("T")[0]
                lines.append(f"[{date_part} {time_part}] @{user}: {text}")
            else:
                lines.append(f"@{user}: {text}")
        return "\n".join(lines)

    def _generate_thread_title(self, messages: list[dict], channel: str) -> str:
        """Generate a descriptive title from the first message."""
        if messages:
            first_msg = messages[0].get("text", "")
            # Take first 60 chars of first message as title
            title = first_msg[:60].replace("\n", " ").strip()
            if len(first_msg) > 60:
                title += "..."
            return f"{channel}: {title}"
        return f"{channel}: Thread"
