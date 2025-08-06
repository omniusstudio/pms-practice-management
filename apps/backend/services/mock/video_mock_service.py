import asyncio
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, cast
from uuid import uuid4

import structlog

logger = structlog.get_logger(__name__)


class VideoMockService:
    """Mock video conferencing service for telehealth sessions.

    Simulates video session creation, management, recording,
    and participant handling for development and testing.
    """

    def __init__(self):
        self.sessions: Dict[str, Dict] = {}
        self.recordings: Dict[str, Dict] = {}
        self.participants: Dict[str, List[Dict]] = {}

    async def create_session(
        self,
        session_name: str,
        max_participants: int = 2,
        recording_enabled: bool = True,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Create a mock video session.

        Args:
            session_name: Name of the session
            max_participants: Maximum number of participants
            recording_enabled: Whether recording is enabled
            metadata: Optional session metadata

        Returns:
            Session object with join URLs and tokens
        """
        await asyncio.sleep(random.uniform(0.1, 0.3))

        session_id = f"session_{uuid4().hex[:16]}"
        room_token = f"token_{uuid4().hex[:32]}"

        # Generate join URLs for different participant types
        provider_url = (
            f"https://video.example.com/room/{session_id}"
            f"?token={room_token}&role=provider"
        )
        patient_url = (
            f"https://video.example.com/room/{session_id}"
            f"?token={room_token}&role=patient"
        )

        session = {
            "id": session_id,
            "name": session_name,
            "status": "created",
            "created_at": datetime.utcnow().isoformat(),
            "max_participants": max_participants,
            "current_participants": 0,
            "recording_enabled": recording_enabled,
            "recording_status": "not_started" if recording_enabled else "disabled",
            "metadata": metadata or {},
            "join_urls": {"provider": provider_url, "patient": patient_url},
            "room_token": room_token,
            "expires_at": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
        }

        self.sessions[session_id] = session
        self.participants[session_id] = []

        await logger.ainfo(
            "Mock video session created",
            session_id=session_id,
            session_name=session_name,
            recording_enabled=recording_enabled,
        )

        return session

    async def join_session(
        self,
        session_id: str,
        participant_name: str,
        participant_role: str = "patient",
        participant_metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Simulate participant joining a session.

        Args:
            session_id: Session ID
            participant_name: Name of participant
            participant_role: Role (provider/patient)
            participant_metadata: Optional participant metadata

        Returns:
            Participant join information
        """
        await asyncio.sleep(random.uniform(0.2, 0.5))

        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if session["current_participants"] >= session["max_participants"]:
            raise ValueError("Session is at maximum capacity")

        participant_id = f"participant_{uuid4().hex[:16]}"

        # Simulate connection scenarios
        connection_scenarios = [
            {"status": "connected", "weight": 0.90},
            {"status": "connection_failed", "weight": 0.05},
            {"status": "audio_only", "weight": 0.05},
        ]

        weights = [cast(float, s["weight"]) for s in connection_scenarios]
        scenario = random.choices(connection_scenarios, weights=weights)[0]

        participant = {
            "id": participant_id,
            "name": participant_name,
            "role": participant_role,
            "status": scenario["status"],
            "joined_at": datetime.utcnow().isoformat(),
            "audio_enabled": scenario["status"] != "connection_failed",
            "video_enabled": scenario["status"] == "connected",
            "metadata": participant_metadata or {},
        }

        if scenario["status"] == "connected":
            session["current_participants"] += 1
            session["status"] = (
                "active" if session["current_participants"] > 1 else "waiting"
            )
            self.participants[session_id].append(participant)

            # Auto-start recording if enabled and session becomes active
            if (
                session["recording_enabled"]
                and session["status"] == "active"
                and session["recording_status"] == "not_started"
            ):
                await self._start_recording(session_id)

        await logger.ainfo(
            "Participant joined session",
            session_id=session_id,
            participant_id=participant_id,
            participant_name=participant_name,
            status=scenario["status"],
        )

        return {
            "participant": participant,
            "session_status": session["status"],
            "recording_status": session["recording_status"],
        }

    async def leave_session(
        self, session_id: str, participant_id: str
    ) -> Dict[str, Any]:
        """Simulate participant leaving a session.

        Args:
            session_id: Session ID
            participant_id: Participant ID

        Returns:
            Updated session information
        """
        await asyncio.sleep(random.uniform(0.1, 0.2))

        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        participants = self.participants.get(session_id, [])
        participant = next((p for p in participants if p["id"] == participant_id), None)

        if participant:
            participant["left_at"] = datetime.utcnow().isoformat()
            participant["status"] = "disconnected"
            session["current_participants"] = max(
                0, session["current_participants"] - 1
            )

            # Update session status
            if session["current_participants"] == 0:
                session["status"] = "ended"
                session["ended_at"] = datetime.utcnow().isoformat()

                # Stop recording if active
                if session["recording_status"] == "recording":
                    await self._stop_recording(session_id)
            elif session["current_participants"] == 1:
                session["status"] = "waiting"

        await logger.ainfo(
            "Participant left session",
            session_id=session_id,
            participant_id=participant_id,
            session_status=session["status"],
        )

        return {
            "session_id": session_id,
            "session_status": session["status"],
            "current_participants": session["current_participants"],
            "recording_status": session["recording_status"],
        }

    async def _start_recording(self, session_id: str) -> None:
        """Start recording for a session.

        Args:
            session_id: Session ID
        """
        session = self.sessions.get(session_id)
        if session and session["recording_enabled"]:
            recording_id = f"rec_{uuid4().hex[:16]}"

            session["recording_status"] = "recording"
            session["recording_id"] = recording_id
            session["recording_started_at"] = datetime.utcnow().isoformat()

            # Create recording entry
            self.recordings[recording_id] = {
                "id": recording_id,
                "session_id": session_id,
                "status": "recording",
                "started_at": datetime.utcnow().isoformat(),
                "file_size_mb": 0,
                "duration_seconds": 0,
            }

            await logger.ainfo(
                "Recording started", session_id=session_id, recording_id=recording_id
            )

    async def _stop_recording(self, session_id: str) -> None:
        """Stop recording for a session.

        Args:
            session_id: Session ID
        """
        session = self.sessions.get(session_id)
        if session and "recording_id" in session:
            recording_id = session["recording_id"]
            recording = self.recordings.get(recording_id)

            if recording:
                # Simulate recording processing
                duration = random.randint(300, 3600)  # 5 min to 1 hour
                file_size = random.randint(50, 500)  # 50MB to 500MB

                recording.update(
                    {
                        "status": "processing",
                        "stopped_at": datetime.utcnow().isoformat(),
                        "duration_seconds": duration,
                        "file_size_mb": file_size,
                        "download_url": (
                            f"https://recordings.example.com/{recording_id}.mp4"
                        ),
                        "expires_at": (
                            datetime.utcnow() + timedelta(days=30)
                        ).isoformat(),
                    }
                )

                session["recording_status"] = "completed"

                await logger.ainfo(
                    "Recording stopped",
                    session_id=session_id,
                    recording_id=recording_id,
                    duration_seconds=duration,
                )

    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information.

        Args:
            session_id: Session ID

        Returns:
            Session information or None if not found
        """
        await asyncio.sleep(random.uniform(0.05, 0.1))

        session = self.sessions.get(session_id)
        if not session:
            return None

        # Include participant information
        participants = self.participants.get(session_id, [])
        session_info = session.copy()
        session_info["participants"] = participants

        return session_info

    async def get_recording_info(self, recording_id: str) -> Optional[Dict[str, Any]]:
        """Get recording information.

        Args:
            recording_id: Recording ID

        Returns:
            Recording information or None if not found
        """
        await asyncio.sleep(random.uniform(0.05, 0.1))
        return self.recordings.get(recording_id)

    async def list_recordings(
        self, session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List recordings, optionally filtered by session.

        Args:
            session_id: Optional session ID to filter by

        Returns:
            List of recording information
        """
        await asyncio.sleep(random.uniform(0.1, 0.2))

        recordings = list(self.recordings.values())

        if session_id:
            recordings = [r for r in recordings if r["session_id"] == session_id]

        return recordings

    async def get_service_health(self) -> Dict[str, Any]:
        """Get mock service health status.

        Returns:
            Service health information
        """
        active_sessions = sum(
            1 for s in self.sessions.values() if s["status"] in ["active", "waiting"]
        )

        recording_sessions = sum(
            1 for s in self.sessions.values() if s["recording_status"] == "recording"
        )

        return {
            "service": "video_mock",
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "stats": {
                "total_sessions": len(self.sessions),
                "active_sessions": active_sessions,
                "recording_sessions": recording_sessions,
                "total_recordings": len(self.recordings),
                "total_participants": sum(len(p) for p in self.participants.values()),
            },
            "uptime_seconds": random.randint(3600, 86400),
        }
